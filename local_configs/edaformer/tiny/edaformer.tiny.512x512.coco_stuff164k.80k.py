_base_ = [
    '../../_base_/models/edaformer.py',
    '../../_base_/datasets/coco-stuff164k.py',
    '../../_base_/default_runtime.py',
    '../../_base_/schedules/schedule_160k_adamw.py'
]

# model settings
norm_cfg = dict(type='SyncBN', requires_grad=True)
find_unused_parameters = True
model = dict(
    type='EncoderDecoder',
    pretrained="EFT_T.pth",
    backbone=dict(
        type='EFT_T',
        style='pytorch',
        reduction_ratios=[1, 1, 1, 1] #  if ISR is applied, adjust this "reduction_ratios". (ex) reduction_ratios=[2, 2, 1, 1]
        ), 
    decode_head=dict(
        type='EDAFormerHead',
        in_channels=[64, 128, 256],
        in_index=[1, 2, 3],
        reduction_ratios=[1, 1, 1], # reduction_ratio_ratios=[2, 2, 2] if ISR is applied
        mlp_ratio=2,
        channels=128,
        dropout_ratio=0.1,
        num_classes=171,
        norm_cfg=norm_cfg,
        align_corners=False,
        decoder_params=dict(embed_dim=128),
        loss_decode=dict(type='CrossEntropyLoss', use_sigmoid=False, loss_weight=1.0)),
    # model training and testing settings
    train_cfg=dict(),
    test_cfg=dict(mode='whole'))

# optimizer
optimizer = dict(_delete_=True, type='AdamW', lr=0.00006, betas=(0.9, 0.999), weight_decay=0.01,
                 paramwise_cfg=dict(custom_keys={'pos_block': dict(decay_mult=0.),
                                                 'norm': dict(decay_mult=0.),
                                                 'head': dict(lr_mult=10.)
                                                 }))

lr_config = dict(_delete_=True, policy='poly',
                 warmup='linear',
                 warmup_iters=1500,
                 warmup_ratio=1e-6,
                 power=1.0, min_lr=0.0, by_epoch=False)
                 
data = dict(samples_per_gpu=4)
evaluation = dict(interval=4000, metric='mIoU')