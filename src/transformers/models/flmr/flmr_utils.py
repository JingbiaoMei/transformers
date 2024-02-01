import torch
import torch.distributed as dist

def get_rank():
    return dist.get_rank()

def get_world_size():
    return dist.get_world_size()

def get_default_group():
    return dist.group.WORLD



# TODO: The masking below might also be applicable in the kNN part
def colbert_score_reduce(scores_padded, D_mask):
    # print('D_mask', D_mask.shape, D_mask)
    D_padding = ~D_mask.view(scores_padded.size(0), scores_padded.size(1)).bool()
    # print('D_padding', D_padding.shape, D_padding)
    # print(D_padding[0].tolist())
    scores_padded[D_padding] = -9999
    scores = scores_padded.max(1).values

    return scores.sum(-1)

def colbert_score(Q, D_padded, D_mask, use_gpu=False):
    """
        Supply sizes Q = (1 | num_docs, *, dim) and D = (num_docs, *, dim).
        If Q.size(0) is 1, the matrix will be compared with all passages.
        Otherwise, each query matrix will be compared against the *aligned* passage.

        EVENTUALLY: Consider masking with -inf for the maxsim (or enforcing a ReLU).
    """
    if use_gpu:
        Q, D_padded, D_mask = Q.cuda(), D_padded.cuda(), D_mask.cuda()

    assert Q.dim() == 3, Q.size()
    assert D_padded.dim() == 3, D_padded.size()
    assert Q.size(0) in [1, D_padded.size(0)]

    scores = D_padded @ Q.to(dtype=D_padded.dtype).permute(0, 2, 1)

    return colbert_score_reduce(scores, D_mask)
