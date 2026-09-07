# FastReID attribution

`src/roadeye/vehicle_encoder.py` adapts inference operations from
[JDAI-CV/fast-reid](https://github.com/JDAI-CV/fast-reid), revision
`c9bc3ceb2f7a6438b62fb515ea3df6d1e999e95d`, under Apache License 2.0
(included in `LICENSE`). Upstream component authorship credits liaoxingyu.

Referenced components: `modeling/backbones/resnet.py`, `layers/batch_norm.py`,
`layers/non_local.py`, `layers/pooling.py`, `modeling/heads/embedding_head.py`,
`modeling/meta_arch/baseline.py`, `data/transforms/build.py`, and the VeRi/Base
YAML configs. The adapter reuses torchvision bottlenecks, limits the architecture
to this released checkpoint, removes training heads, and adds strict checksum
and state-dictionary checks. It retains the release's one-channel non-local
blocks, unpadded ceil-mode max pool, final stride 1, IBN, GeM, and BN neck.

Weights: official `v0.1.1/veri_sbs_R50-ibn.pth`, SHA-256
`57fb9c17d88911ea64390bf5427f43511435e7f88f6eed9dbc969d4b611e53cd`.
The published config declares VeRi training. No CityFlow training is performed
by RoadEye. The weight file remains local and ignored; no dataset or model
redistribution rights beyond the upstream terms are asserted.

[Model/config source](https://github.com/JDAI-CV/fast-reid/blob/c9bc3ceb2f7a6438b62fb515ea3df6d1e999e95d/configs/VeRi/sbs_R50-ibn.yml).
Upstream benchmark numbers are not RoadEye results and are not repeated as
RoadEye accuracy claims.
