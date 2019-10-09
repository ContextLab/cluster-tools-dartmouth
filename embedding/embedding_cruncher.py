#!/usr/bin/python

import os
import sys
import math
import pickle
import pycircstat
import numpy as np
import pandas as pd
import hypertools as hyp
import matplotlib as mpl
import matplotlib.pyplot as plt
from os.path import join as opj
from statsmodels.stats.multitest import multipletests as mt
from embedding_config import config

cmap = plt.cm.Spectral

np_seed = int(sys.argv[1])

ep_events_dir = opj(config['datadir'], 'events', 'episodes')
rec_events_dir = opj(config['datadir'], 'events', 'recalls')
pickle_dir = opj(config['datadir'], 'pickles')

embeddings_dir = opj(config['datadir'], 'embeddings')
fig_dir = opj(config['datadir'], 'figures')

episode_events = {ep: np.load(opj(ep_events_dir, f'{ep}_events.npy'))
                  for ep in ['atlep1', 'atlep2', 'arrdev']}

recall_events = {rectype: {} for rectype in ['atlep1', 'delayed', 'atlep2', 'arrdev']}
avg_recall_events = dict.fromkeys(recall_events)
event_mappings = dict.fromkeys(recall_events)
for root, dirs, files in os.walk(rec_events_dir):
    event_models = [f for f in files if f.endswith('npy')]
    rectype = os.path.split(root)[-1]
    if rectype == 'prediction':
        continue
    for f_name in event_models:
        m = np.load(opj(root, f_name), allow_pickle=True)
        if f_name.startswith('debug'):
            recall_events[rectype][os.path.splitext(f_name)[0]] = m
        elif f_name.startswith('avg_events'):
            avg_recall_events[rectype] = m
        else:
            event_mappings[rectype] = m

# session 1/session 2 psiturk ID mappings
id_maps = pd.read_pickle(opj(pickle_dir, 'id_maps.p'))


class Point:
    def __init__(self, coord=None):
        self.coord = np.array(coord)


class LineSegment:
    def __init__(self, p1=None, p2=None):
        if isinstance(p1, Point):
            self.p1 = p1
        else:
            self.p1 = Point(p1)

        if isinstance(p2, Point):
            self.p2 = p2
        else:
            self.p2 = Point(p2)

    def intersect(self, z):
        if isinstance(z, Circle):
            return _seg_intersect_circle(self, z)
        elif isinstance(z, Rectangle):
            return _seg_intersect_rect(self, z)

    def norm(self):
        diff = self.p2.coord - self.p1.coord
        return diff / np.linalg.norm(diff)

    def get_p1(self):
        return self.p1.coord

    def get_p2(self):
        return self.p2.coord

    def get_vec(self):
        return self.p2.coord - self.p1.coord

    def angle(self, ref=None):
        if ref == None:
            p1 = np.zeros_like(self.get_p1())
            p2 = np.zeros_like(self.get_p1())
            p2[0] = 1
            ref = LineSegment(p1, p2)
        v0 = ref.get_vec()
        v1 = self.get_vec()
        return np.arccos(v0.dot(v1) / (np.linalg.norm(v0) * np.linalg.norm(v1)))


class Circle:
    def __init__(self, center=None, r=None):
        self.center = np.array(center)
        self.r = r

    def get_center(self):
        return self.center

    def get_radius(self):
        return self.r


class Rectangle:
    def __init__(self, x=None, y=None, w=None):
        self.c0 = x-w
        self.c1 = y-w
        self.c2 = x+w
        self.c3 = y+w


def _seg_intersect_circle(ls, circ):
    Q = circ.get_center()
    r = circ.get_radius()
    P1 = ls.get_p1()
    V = ls.get_p2() - P1

    a = V.dot(V)
    b = 2 * V.dot(P1 - Q)
    c = P1.dot(P1) + Q.dot(Q) - 2 * P1.dot(Q) - r ** 2

    disc = b ** 2 - 4 * a * c
    if disc < 0:
        return False

    sqrt_disc = math.sqrt(disc)
    t1 = (-b + sqrt_disc) / (2 * a)
    t2 = (-b - sqrt_disc) / (2 * a)
    if not (0 <= t1 <= 1 or 0 <= t2 <= 1):
        return False

    return True


def _seg_intersect_rect(ls, r):
    # find min/max X for the segment
    minX = min(ls.p1.x, ls.p2.x)
    maxX = max(ls.p1.x, ls.p2.x)

    # find the intersection of the segment's and rectangle's x-projections
    if maxX > r.c2:
        maxX = r.c2
    if minX < r.c0:
        minX = r.c0

    if minX > maxX:
        return False

    minY = ls.p1.y
    maxY = ls.p2.y

    dx = ls.p2.x - ls.p1.x

    if abs(dx) > .0000001:
        a = (ls.p2.y - ls.p1.y) / dx
        b = ls.p1.y - a * ls.p1.x
        minY = a * minX + b
        maxY = a * maxX + b

    if minY > maxY:
        tmp = maxY
        maxY = minY
        minY = tmp

    # find the intersection of the segment's and rectangle's y-projections
    if maxY > r.c3:
        maxY = r.c3
    if minY < r.c1:
        minY = r.c1

    # if Y-projections do not intersect return false
    if minY > maxY:
        return False
    else:
        return True


def add_arrows(axes, x, y, minifig=False, **kwargs):
    if minifig:
        aspace = 0.1
    else:
        aspace = .05

    aspace *= scale

    r = [0]
    for i in range(1, len(x)):
        dx = x[i] - x[i - 1]
        dy = y[i] - y[i - 1]
        r.append(np.sqrt(dx * dx + dy * dy))
    r = np.array(r)

    rtot = []
    for i in range(len(r)):
        rtot.append(r[0:i].sum())
    rtot.append(r.sum())

    arrowData = []
    arrowPos = 0
    rcount = 1
    while arrowPos < r.sum():
        x1, x2 = x[rcount - 1], x[rcount]
        y1, y2 = y[rcount - 1], y[rcount]
        da = arrowPos - rtot[rcount]
        theta = np.arctan2((x2 - x1), (y2 - y1))
        ax = np.sin(theta) * da + x1
        ay = np.cos(theta) * da + y1
        arrowData.append((ax, ay, theta))
        arrowPos += aspace
        while arrowPos > rtot[rcount + 1]:
            rcount += 1
            if arrowPos > rtot[-1]:
                break

    for ax, ay, theta in arrowData:
        axes.arrow(ax, ay,
                   np.sin(theta) * aspace / 10, np.cos(theta) * aspace / 10,
                   head_width=aspace / 3, **kwargs)


def compute_coord(xi, yi, w, seglist, kind='rectangle'):
    if kind == 'rectangle':
        z = Rectangle(x=xi, y=yi, w=w)
    elif kind == 'circle':
        z = Circle(center=[xi, yi], r=w)

    segs = list(filter(lambda s: s.intersect(z), seglist))

    if len(segs) > 1:
        u, v = np.array([seg.norm() for seg in segs]).mean(0)
        rads = np.array([seg.angle() for seg in segs])
        p, z = pycircstat.tests.rayleigh(rads)
    else:
        u = 0
        v = 0
        p = 1
    c = len(segs)
    return u, v, p, c


# filter video events with no successful recalls from average recall events model
for rectype in avg_recall_events.keys():
    no_rec_mask = np.all(np.equal(avg_recall_events[rectype], 0), axis=1)
    avg_recall_events[rectype] = avg_recall_events[rectype][~no_rec_mask]


embeddings = {rectype: {} for rectype in recall_events.keys()}

for ep in ['atlep1', 'atlep2', 'arrdev']:
    data = [episode_events[ep], avg_recall_events[ep]]

    if ep == 'atlep1':
        data.append(avg_recall_events['delayed'])

    turkids = []
    for turkid, evs in recall_events[ep].items():
        turkids.append(turkid)
        data.append(evs)

    if ep == 'atlep1':
        turkids_del = []
        for turkid, evs in recall_events['delayed'].items():
            turkids_del.append(turkid)
            data.append(evs)

    np.random.seed(np_seed)
    embs = hyp.reduce(data, reduce='UMAP', ndims=2)

    episode = embs.pop(0)
    embeddings[ep]['episode'] = episode
    embeddings[ep]['avg_recall'] = embs.pop(0)

    if ep == 'atlep1':
        embeddings['delayed']['episode'] = episode
        embeddings['delayed']['avg_recall'] = embs.pop(0)

    embeddings[ep]['recalls'] = {}
    for turkid in turkids:
        embeddings[ep]['recalls'][turkid] = embs.pop(0)

    embeddings[ep]['mapping'] = event_mappings[ep]

    if ep == 'atlep1':
        embeddings['delayed']['mapping'] = event_mappings['delayed']
        embeddings['delayed']['recalls'] = {}
        for turkid in turkids_del:
            embeddings['delayed']['recalls'][turkid] = embs.pop(0)


for rectype, embs in embeddings.items():
    with open(opj(embeddings_dir, rectype, f'np{np_seed}_umap{0}.p'), 'wb') as f:
        pickle.dump(embs, f)

    episode = embs['episode']
    avg_recall = embs['avg_recall']
    recalls = embs['recalls']
    mappings = embs['mapping']

    # create 2D grid
    scale = np.abs(episode).max()
    step = scale / 25
    X, Y = np.meshgrid(np.arange(-scale, scale, step), np.arange(-scale, scale, step))

    # turn embedded recall event model into a list of line segments
    seglist = []
    for i, (turkid, sub_emb) in enumerate(recalls.items()):
        for j in range(sub_emb.shape[0] - 1):
            p1 = Point(coord=sub_emb[j, :])
            p2 = Point(coord=sub_emb[j + 1, :])
            seg = LineSegment(p1=p1, p2=p2)

            seglist.append(seg)

    # compute the average vector and p-value at each grid point
    U = np.zeros_like(X)
    V = np.zeros_like(X)
    P = np.zeros_like(X)
    Z = np.zeros_like(X)
    C = np.zeros_like(X)
    for i, (x, y) in enumerate(zip(X, Y)):
        for j, (xi, yi) in enumerate(zip(x, y)):
            U[i, j], V[i, j], P[i, j], C[i, j] = compute_coord(xi, yi, step * 2, seglist, kind='circle')

    # multiple comparisons correction
    thresh = .001
    Pc = mt(P.ravel(), method='fdr_bh', alpha=.05)[1].reshape(np.shape(X))
    M = np.hypot(U, V)
    M = plt.cm.Blues(M)
    M[Pc > thresh] = [.5, .5, .5, .1]
    M[Pc == 1] = [.5, .5, .5, 0]

    # create figure with subplots
    plt.figure(figsize=(12, (len(recalls) // 8) * 2))
    mpl.rcParams['pdf.fonttype'] = 42
    axarr = [0 for i in range(2)]

    axarr[0] = plt.subplot2grid((len(recalls) // 8 + 3, 8), (0, 1), colspan=3, rowspan=2)
    axarr[1] = plt.subplot2grid((len(recalls) // 8 + 3, 8), (0, 4), colspan=3, rowspan=2)

    for i in range(2, (len(recalls) // 8 + 3)):
        for j in range(0, 8):
            ax = plt.subplot2grid((len(recalls) // 8 + 3, 8), (i, j))
            axarr.append(ax)

    # plot episode trajectory and events
    axarr[0].scatter(episode[:, 0], episode[:, 1], c=range(episode.shape[0]),
                     cmap=cmap, s=150, zorder=3)
    axarr[0].scatter(episode[:, 0], episode[:, 1], c='k', cmap=cmap, s=200, zorder=2)
    axarr[0].plot(episode[:, 0], episode[:, 1], zorder=1, c='k', alpha=.5)
    add_arrows(axarr[0], episode[:, 0], episode[:, 1], zorder=0, alpha=1, color='k', fill=True)
    axarr[0].set_title('Episode events')
    axarr[0].set_xlim(episode.min(0)[0] - 1, episode.max(0)[0] + 1)
    axarr[0].set_ylim(episode.min(0)[1] - 1, episode.max(0)[1] + 1)
    axarr[0].text(0, 1, 'A', horizontalalignment='center', transform=axarr[0].transAxes, fontsize=18)

    # plot average recall events
    axarr[1].quiver(X, Y, U, V, color=M.reshape(M.shape[0] * M.shape[1], 4), zorder=1, width=.004)
    axarr[1].plot(avg_recall[:, 0], avg_recall[:, 1], zorder=2, c='k', alpha=1)
    axarr[1].plot(episode[:, 0], episode[:, 1], zorder=1, c='k', alpha=.5)
    add_arrows(axarr[1], avg_recall[:, 0], avg_recall[:, 1], zorder=3, alpha=1, color='k', fill=True)
    axarr[1].scatter(avg_recall[:, 0], avg_recall[:, 1], c=range(avg_recall.shape[0]), cmap=cmap,
                     s=150, zorder=4)
    axarr[1].scatter(avg_recall[:, 0], avg_recall[:, 1], c='k', cmap=cmap, s=200, zorder=3)
    axarr[1].set_title('Average recall events')
    axarr[1].set_xlim(episode.min(0)[0] - 1, episode.max(0)[0] + 1)
    axarr[1].set_ylim(episode.min(0)[1] - 1, episode.max(0)[1] + 1)
    axarr[1].text(0, 1, 'B',
                  horizontalalignment='center',
                  transform=axarr[1].transAxes,
                  fontsize=18)

    # plot individual recalls
    axarr[2].text(0, 1.05, 'C', horizontalalignment='center', transform=axarr[2].transAxes, fontsize=18)

    if rectype == 'atlep1':
        ids = id_maps['session 1']
    elif rectype == 'delayed':
        ids = id_maps['session 2']
    elif rectype == 'atlep2':
        ids = id_maps.loc[id_maps.index.str.contains('A'), 'session 2']
    else:
        ids = id_maps.loc[id_maps.index.str.contains('B'), 'session 2']

    for i, turkid in enumerate(ids, start=2):
        rec_emb = recalls[turkid]
        m = mappings[np.where(mappings.T[0] == turkid)].ravel()[1]
        axarr[i].scatter(rec_emb[:, 0], rec_emb[:, 1], c=cmap(m / len(episode)), cmap=cmap, s=60, zorder=2)
        axarr[i].plot(rec_emb[:, 0], rec_emb[:, 1], zorder=1, c='k', alpha=.25)
        axarr[i].plot(avg_recall[:, 0], avg_recall[:, 1], zorder=3, c='k', alpha=1)
        add_arrows(axarr[i], rec_emb[:, 0], rec_emb[:, 1], zorder=1, alpha=.25, color='k', minifig=True, fill=True)
        axarr[i].set_xlim(episode.min(0)[0] - 1, episode.max(0)[0] + 1)
        axarr[i].set_ylim(episode.min(0)[1] - 1, episode.max(0)[1] + 1)
        axarr[i].set_title(f'P{i}')

    for a in axarr:
        a.axis('off')

    plt.tight_layout()
    plt.subplots_adjust(wspace=0, hspace=0.25)
    plt.savefig(opj(fig_dir, rectype, f'np{np_seed}_umap{0}.pdf'))




