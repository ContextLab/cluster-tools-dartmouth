import os
import pickle
from time import sleep, localtime, asctime
import numpy as np
from os.path import join as opj
from scipy.spatial.distance import pdist, cdist
from embedding_config import config

try:
    from tqdm import trange
    range_ = trange
except ModuleNotFoundError:
    range_ = range


# Define some functions
##################################################
def r2z(r):
    with np.errstate(invalid='ignore', divide='ignore'):
        return 0.5 * (np.log(1 + r) - np.log(1 - r))


def spatial_similarity(embedding, original_pdist, emb_metric, z_transform=False):
    """
    computes correlation between pairwise euclidean distance in embedding space
    and correlation distance in original space
    """
    emb_pdist = pdist(embedding, emb_metric)
    if emb_metric == 'correlation':
        emb_pdist = 1 - emb_pdist
        if z_transform:
            emb_pdist = r2z(emb_pdist)
            original_pdist = r2z(original_pdist)
    return 1 - pdist((emb_pdist, original_pdist), 'correlation')[0]


# source: https://stackoverflow.com/questions/563198/how-do-you-detect-where-two-line-segments-intersect
def _segments_intersect2d(a1, b1, a2, b2):
    s1 = b1 - a1
    s2 = b2 - a2

    s = (-s1[1] * (a1[0] - a2[0]) + s1[0] * (a1[1] - a2[1])) / (-s2[0] * s1[1]
                                                                + s1[0] * s2[1])
    t = (s2[0] * (a1[1] - a2[1]) - s2[1] * (a1[0] - a2[0])) / (-s2[0] * s1[1]
                                                               + s1[0] * s2[1])

    if (s >= 0) and (s <= 1) and (t >= 0) and (t <= 1):
        return True
    else:
        return False


def n_intersections(x):
    intersections = 0
    points = []
    for i in np.arange(x.shape[0] - 1):
        a1 = x[i, :]
        b1 = x[i + 1, :]
        for j in np.arange(i + 2, x.shape[0] - 1):
            a2 = x[j, :]
            b2 = x[j + 1, :]

            if _segments_intersect2d(a1, b1, a2, b2):
                intersections += 1
    return intersections


def dispersion_dist(embedding):
    center = embedding.mean(axis=0)
    return cdist(np.atleast_2d(center), embedding, 'euclidean').mean()


##################################################

embeddings_dir = opj(config['datadir'], 'embeddings')
events_dir = opj(config['datadir'], 'events', 'episodes')
last_created = opj(embeddings_dir, 'arrdev', 'np50_umap200.p')

ep_events_pdists = {}
for rectype in ['atlep1', 'delayed', 'atlep2', 'arrdev']:
    ep = 'atlep1' if rectype == 'delayed' else rectype
    ep_events = np.load(opj(events_dir, f'{ep}_events.npy'))
    ep_events_pdists[rectype] = 1 - pdist(ep_events, 'correlation')

# while not os.path.isfile(last_created):
#     sleep(60)

print(f'Started: {asctime(localtime())}')
results = {rectype: {} for rectype in ep_events_pdists.keys()}
for rectype, res in results.items():
    emb_rtdir = opj(embeddings_dir, rectype)
    print(f'optimizing {rectype}...')
    dispersion = np.full((200, 200), np.nan)
    intersections = np.full((200, 200), np.nan)
    similarity_euc = np.full((200, 200), np.nan)
    similarity_corr = np.full((200, 200), np.nan)
    similarity_zcorr = np.full((200, 200), np.nan)

    for np_seed in range_(200):
        for umap_seed in range(200):
            f_name = f'np{np_seed}_umap{umap_seed}.p'
            fpath = opj(emb_rtdir, f_name)
            try:
                with open(fpath, 'rb') as f:
                    ep_emb = pickle.load(f)['episode']

            except FileNotFoundError:
                print(f'File not found: {rectype}/{f_name}')
                continue

            ix = np_seed, umap_seed
            dispersion[ix] = dispersion_dist(ep_emb)
            intersections[ix] = n_intersections(ep_emb)
            similarity_euc[ix] = spatial_similarity(ep_emb,
                                                    ep_events_pdists[rectype],
                                                    'euclidean')
            similarity_corr[ix] = spatial_similarity(ep_emb,
                                                     ep_events_pdists[rectype],
                                                     'correlation')
            similarity_zcorr[ix] = spatial_similarity(ep_emb,
                                                      ep_events_pdists[rectype],
                                                      'correlation',
                                                      z_transform=True)

    dist_np, dist_umap = np.unravel_index(np.nanargmax(dispersion), dispersion.shape)
    res['dispersion'] = f'np{dist_np}_umap{dist_umap}'

    intersect_np, intersect_umap = np.unravel_index(np.nanargmin(intersections),
                                                    intersections.shape)
    res['intersections'] = f'np{intersect_np}_umap{intersect_umap}'

    sim_euc_np, sim_euc_umap = np.unravel_index(np.nanargmax(similarity_euc),
                                                similarity_euc.shape)
    res['similarity_euc'] = f'np{sim_euc_np}_umap{sim_euc_umap}'

    sim_corr_np, sim_corr_umap = np.unravel_index(np.nanargmax(similarity_corr),
                                                  similarity_corr.shape)
    res['similarity_corr'] = f'np{sim_corr_np}_umap{sim_corr_umap}'

    sim_zcorr_np, sim_zcorr_umap = np.unravel_index(np.nanargmax(similarity_zcorr),
                                                    similarity_zcorr.shape)
    res['similarity_zcorr'] = f'np{sim_zcorr_np}_umap{sim_zcorr_umap}'

with open(opj(config['datadir'], 'optimal_seeds.p'), 'wb') as f:
    pickle.dump(results, f)

print(f'Ended: {asctime(localtime())}')
