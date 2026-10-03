#!/usr/bin/env python3
"""Frozen CPU pilot on owner-mirror real catalogue data; never approves a slot."""
import sys
import argparse
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import torch

# Run from an uninstalled checkout exactly as documented (`python scripts/<name>.py`):
# make the in-repo package importable without `pip install -e .`.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from gemsdoe30.cv import spatial_quadrant_masks, compare_spatial_holdout
from gemsdoe30.geology import interaction_features
from gemsdoe30.losses import GEMSBoundaryAwareLoss
from gemsdoe30.normalization import fit_robust_feature_stats
from gemsdoe30.training import RandomPatchDataset
from gemsdoe30.analysis import near_miss_profile


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def fit_predict(raw, derived, labels, valid, train, heldout, seed, arm, dest):
    # Matching raw-channel normalization and samples irrespective of added features.
    raw_stats = fit_robust_feature_stats(raw, train, seed=seed)
    feature_stats = raw_stats + fit_robust_feature_stats(derived, train, seed=seed)
    data = np.lib.format.open_memmap(dest/'features.npy', mode='w+', dtype=np.float32,
                                    shape=(22, *labels.shape))
    data[:19] = raw
    data[19:] = derived
    data.flush()
    ds = RandomPatchDataset(data, labels, valid, train, patch_size=64, samples=80,
                            seed=seed, feature_stats=feature_stats)
    torch.manual_seed(seed)
    model = torch.nn.Sequential(torch.nn.Conv2d(22,24,1), torch.nn.ReLU(), torch.nn.Conv2d(24,1,1))
    opt = torch.optim.AdamW(model.parameters(), lr=.001, weight_decay=.0001)
    criterion = GEMSBoundaryAwareLoss(boundary_weight=0 if arm == 'R' else .5)
    history = []
    for epoch in range(3):
        ds.set_epoch(epoch)
        model.train()
        losses = []
        for x,y,v,s in torch.utils.data.DataLoader(ds,batch_size=2,shuffle=False,num_workers=0):
            opt.zero_grad(set_to_none=True)
            parts = criterion(model(x),y,v,s,return_components=True)
            parts['total'].backward()
            opt.step()
            losses.append([float(parts[k].detach()) for k in ('total','regional','boundary')])
        history.append(np.mean(losses,axis=0).tolist())
    checkpoint = dest/'checkpoint.pt'
    torch.save({'state_dict':model.state_dict(), 'feature_stats':feature_stats,'history':history,
                'seed':seed,'arm':arm}, checkpoint)
    pred = np.lib.format.open_memmap(dest/'prediction.npy', mode='w+', dtype=np.float32, shape=labels.shape)
    pred[:] = np.nan
    # 1x1 model has no tile-context edge issue; normalize and infer on heldout pixels only.
    med = np.array([s['median'] for s in feature_stats],dtype=np.float32)[:,None,None]
    iqr = np.array([s['iqr'] for s in feature_stats],dtype=np.float32)[:,None,None]
    model.eval()
    with torch.no_grad():
        for y in range(0,labels.shape[0],128):
            for x in range(0,labels.shape[1],256):
                ys,xs = slice(y,y+128),slice(x,x+256)
                mask = heldout[ys,xs]
                if not mask.any(): continue
                block = np.asarray(data[:,ys,xs]).copy()
                block = np.nan_to_num(np.clip((block-med)/iqr,-8,8),nan=0,posinf=0,neginf=0)
                p = torch.sigmoid(model(torch.from_numpy(block[None])))[0,0].numpy()
                pred[ys,xs][mask] = p[mask]
    pred.flush()
    data_path = dest/'features.npy'
    del data
    data_path.unlink()
    return pred, {'seed':seed,'arm':arm,'history_total_regional_boundary':history,
                  'checkpoint_sha256':sha(checkpoint),'prediction_sha256':sha(dest/'prediction.npy'),
                  'heldout_pixels':int(heldout.sum()),'training_pixels':int(train.sum())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',type=Path,default=Path('data/processed'))
    parser.add_argument('--output-dir',type=Path,default=Path('runs/geology-pilot'))
    parser.add_argument('--seed',type=int,default=30)
    args = parser.parse_args()
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    manifest = json.loads((args.data_dir/'manifest.json').read_text())
    raw = np.load(args.data_dir/'features_raw.npy',mmap_mode='r')
    labels = np.load(args.data_dir/'labels.npy',mmap_mode='r')
    valid = np.load(args.data_dir/'valid.npy') & np.load(args.data_dir/'label_valid.npy')
    if raw.shape[0] != 19: raise ValueError('pilot requires audited 19-band input')
    h,c = interaction_features(raw,manifest['feature_band_names'])
    zeros = np.zeros_like(h)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    mosaics = {}
    receipts = []
    for arm,derived in [('R',zeros),('G',zeros),('C',c),('H',h)]:
        mosaic = np.lib.format.open_memmap(args.output_dir/f'{arm}-oof.npy',mode='w+',dtype=np.float32,shape=labels.shape)
        mosaic[:] = np.nan
        for fold in range(4):
            print(f'seed={args.seed} arm={arm} fold={fold}',flush=True)
            train, heldout = spatial_quadrant_masks(valid,fold,buffer_m=800)
            dest = args.output_dir/f'{arm}-f{fold}'
            dest.mkdir(exist_ok=True)
            prediction,receipt = fit_predict(raw,derived,labels,valid,train,heldout,args.seed,arm,dest)
            mosaic[heldout] = prediction[heldout]
            receipt['fold'] = fold
            receipts.append(receipt)
        mosaic.flush()
        mosaics[arm] = mosaic
    comparisons = {arm:compare_spatial_holdout(labels,mosaics['R'],mosaics[arm],valid,buffer_m=800)
                   for arm in ('G','C','H')}
    controls = {'R': comparisons['H']['pooled_baseline']['dti'],
                'G':comparisons['G']['pooled_candidate']['dti'],
                'C':comparisons['C']['pooled_candidate']['dti']}
    best = max(controls,key=controls.get)
    gate_comparison = compare_spatial_holdout(labels,mosaics[best],mosaics['H'],valid,buffer_m=800)
    passed = gate_comparison['pooled_delta_dti'] >= .002 and sum(
        row['fold_isolated_delta_dti'] > 0 for row in gate_comparison['folds']) >= 3
    report = {'created_utc':datetime.now(timezone.utc).isoformat(),'seed':args.seed,
              'dataset_signature':manifest['dataset_signature'],
              'preregistration_sha256':sha('docs/research/pilot-preregistration.md'),
              'scope':'real owner-mirror catalogue spatial proxy; not new-fault test or competition score',
              'mask':'identical full labelled footprint for all arms; missing features zero-imputed after fold-local scaling',
              'valid_pixels':int(valid.sum()),'positive_pixels':int(((labels==1)&valid).sum()),
              'buffer_m':800,'feature_max_support_m':500,'receipts':receipts,
              'controls_dti':controls,'comparisons_to_R':comparisons,'best_control':best,
              'H_vs_best':gate_comparison,'screen_passed':passed,
              'near_miss_profiles':{arm:near_miss_profile(p,labels,valid) for arm,p in mosaics.items()},
              'slot_approved':False,'decision':'fresh-seed confirmation required; no slot' if passed else 'screen failed; no slot',
              'oof_sha256':{arm:sha(args.output_dir/f'{arm}-oof.npy') for arm in mosaics}}
    (args.output_dir/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['controls_dti','best_control','screen_passed','decision']},indent=2))


if __name__ == '__main__': main()
