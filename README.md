# Embedding-Free Transformer with Inference Spatial Reduction for Efficient Semantic Segmentation (ECCV 2024)


This repository contains the official Pytorch implementation of training & evaluation code and the pretrained models for ISR method and EDAFormer. The paper is in [Here](https://arxiv.org/abs/2407.17261).


## Installation

For install and data preparation, please refer to the guidelines in [MMSegmentation v0.13.0](https://github.com/open-mmlab/mmsegmentation/tree/v0.13.0).

Other requirements:
```pip install timm==0.3.2```

An example (works for me): ```CUDA 11.1``` and  ```pytorch 1.8.0``` 

```
pip install torchvision==0.8.2
pip install timm==0.3.2
pip install mmcv-full==1.2.7
pip install opencv-python==4.5.1.48
cd EDAFormer && pip install -e . --user
```

## Evaluation
  
Download [EDAFormer weights](https://drive.google.com/drive/u/0/folders/1hiAFQcfH9qd37WOc1_HMB0vKzbY-IWrO) into the `/path/to/checkpoint_file`.

```local_configs/``` contains config files. To apply our ```ISR method```, adjust ```--backbone_reduction_ratios``` and ```--decoder_reduction_ratios```.


Example: Evaluate ```EDAFormer-T``` on ```ADE20K```:

```
# Single-gpu testing
CUDA_VISIBLE_DEVICES=0 python ./tools/test.py local_configs/edaformer/tiny/edaformer.tiny.512x512.ade.160k.py /path/to/checkpoint_file

# Multi-gpu testing
CUDA_VISIBLE_DEVICES=0,1,2,3 bash ./tools/dist_test.sh local_configs/edaformer/tiny/edaformer.tiny.512x512.ade.160k.py /path/to/checkpoint_file <GPU_NUM>

# Multi-gpu, multi-scale testing
CUDA_VISIBLE_DEVICES=0,1,2,3 bash ./tools/dist_test.sh local_configs/edaformer/tiny/edaformer.tiny.512x512.ade.160k.py /path/to/checkpoint_file <GPU_NUM> --aug-test
```


Example: Evaluate ```EDAFormer-T``` with ```ISR``` on ```ADE20K```:

```
# Single-gpu testing
CUDA_VISIBLE_DEVICES=0 python ./tools/test.py local_configs/edaformer/tiny/edaformer.tiny.512x512.ade.160k.py /path/to/checkpoint_file --backbone_reduction_ratios "2211" --decoder_reduction_ratios "222"

# Multi-gpu testing
CUDA_VISIBLE_DEVICES=0,1,2,3 bash ./tools/dist_test.sh local_configs/edaformer/tiny/edaformer.tiny.512x512.ade.160k.py /path/to/checkpoint_file <GPU_NUM> --backbone_reduction_ratios "2211" --decoder_reduction_ratios "222"

# Multi-gpu, multi-scale testing
CUDA_VISIBLE_DEVICES=0,1,2,3 bash ./tools/dist_test.sh local_configs/edaformer/tiny/edaformer.tiny.512x512.ade.160k.py /path/to/checkpoint_file <GPU_NUM> --aug-test --backbone_reduction_ratios "2211" --decoder_reduction_ratios "222"
```

## Training

Example: Train ```EDAFormer-T``` on ```ADE20K```:

```
# Single-gpu training
CUDA_VISIBLE_DEVICES=0 python ./tools/train.py local_configs/edaformer/tiny/edaformer.tiny.512x512.ade.160k.py 

# Multi-gpu training
CUDA_VISIBLE_DEVICES=0,1,2,3 bash ./tools/dist_train.sh local_configs/edaformer/tiny/edaformer.tiny.512x512.ade.160k.py <GPU_NUM>
```
