# coding=utf-8
# Copyright 2024 FLMR Authors, The Hugging Face Team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
""" PyTorch FLMR model for Open Domain Question Answering."""


from dataclasses import dataclass
from typing import Optional, Tuple, Union, List

import torch
from torch import Tensor, nn

from ...modeling_outputs import BaseModelOutputWithPooling
from ...modeling_utils import PreTrainedModel
from ...utils import (
    ModelOutput,
    add_start_docstrings,
    add_start_docstrings_to_model_forward,
    logging,
    replace_return_docstrings,
)
from ..bert.modeling_bert import BertModel
from .configuration_flmr import FLMRConfig


logger = logging.get_logger(__name__)

_CONFIG_FOR_DOC = "FLMRConfig"
_CHECKPOINT_FOR_DOC = "weizhelin/flmr"

FLMR_PRETRAINED_MODEL_ARCHIVE_LIST = [
    "weizhelin/flmr",
    # See all FLMR models at https://huggingface.co/models?filter=flmr
]

FLMR_PRETRAINED_MODEL_ARCHIVE_LIST = [
    "weizhelin/flmr",
    # See all FLMR models at https://huggingface.co/models?filter=flmr
]

FLMR_PRETRAINED_MODEL_ARCHIVE_LIST = [
    "weizhelin/flmr",
    # See all FLMR models at https://huggingface.co/models?filter=flmr
]



##########
# Outputs
##########


@dataclass
class FLMRContextEncoderOutput(ModelOutput):
    """
    Class for outputs of [`FLMRQuestionEncoder`].

    Args:
        pooler_output (`torch.FloatTensor` of shape `(batch_size, embeddings_size)`):
            The FLMR encoder outputs the *pooler_output* that corresponds to the context representation. Last layer
            hidden-state of the first token of the sequence (classification token) further processed by a Linear layer.
            This output is to be used to embed contexts for nearest neighbors queries with questions embeddings.
        hidden_states (`tuple(torch.FloatTensor)`, *optional*, returned when `output_hidden_states=True` is passed or when `config.output_hidden_states=True`):
            Tuple of `torch.FloatTensor` (one for the output of the embeddings + one for the output of each layer) of
            shape `(batch_size, sequence_length, hidden_size)`.

            Hidden-states of the model at the output of each layer plus the initial embedding outputs.
        attentions (`tuple(torch.FloatTensor)`, *optional*, returned when `output_attentions=True` is passed or when `config.output_attentions=True`):
            Tuple of `torch.FloatTensor` (one for each layer) of shape `(batch_size, num_heads, sequence_length,
            sequence_length)`.

            Attentions weights after the attention softmax, used to compute the weighted average in the self-attention
            heads.
    """

    pooler_output: torch.FloatTensor
    late_interaction_output: torch.FloatTensor = None
    hidden_states: Optional[Tuple[torch.FloatTensor]] = None
    attentions: Optional[Tuple[torch.FloatTensor]] = None
    context_mask: Optional[Tensor] = None


@dataclass
class FLMRQuestionEncoderOutput(ModelOutput):
    """
    Class for outputs of [`FLMRQuestionEncoder`].

    Args:
        pooler_output (`torch.FloatTensor` of shape `(batch_size, embeddings_size)`):
            The FLMR encoder outputs the *pooler_output* that corresponds to the question representation. Last layer
            hidden-state of the first token of the sequence (classification token) further processed by a Linear layer.
            This output is to be used to embed questions for nearest neighbors queries with context embeddings.
        hidden_states (`tuple(torch.FloatTensor)`, *optional*, returned when `output_hidden_states=True` is passed or when `config.output_hidden_states=True`):
            Tuple of `torch.FloatTensor` (one for the output of the embeddings + one for the output of each layer) of
            shape `(batch_size, sequence_length, hidden_size)`.

            Hidden-states of the model at the output of each layer plus the initial embedding outputs.
        attentions (`tuple(torch.FloatTensor)`, *optional*, returned when `output_attentions=True` is passed or when `config.output_attentions=True`):
            Tuple of `torch.FloatTensor` (one for each layer) of shape `(batch_size, num_heads, sequence_length,
            sequence_length)`.

            Attentions weights after the attention softmax, used to compute the weighted average in the self-attention
            heads.
    """

    pooler_output: torch.FloatTensor
    late_interaction_output: torch.FloatTensor = None
    hidden_states: Optional[Tuple[torch.FloatTensor]] = None
    attentions: Optional[Tuple[torch.FloatTensor]] = None


@dataclass
class FLMRReaderOutput(ModelOutput):
    """
    Class for outputs of [`FLMRQuestionEncoder`].

    Args:
        start_logits (`torch.FloatTensor` of shape `(n_passages, sequence_length)`):
            Logits of the start index of the span for each passage.
        end_logits (`torch.FloatTensor` of shape `(n_passages, sequence_length)`):
            Logits of the end index of the span for each passage.
        relevance_logits (`torch.FloatTensor` of shape `(n_passages, )`):
            Outputs of the QA classifier of the FLMRReader that corresponds to the scores of each passage to answer the
            question, compared to all the other passages.
        hidden_states (`tuple(torch.FloatTensor)`, *optional*, returned when `output_hidden_states=True` is passed or when `config.output_hidden_states=True`):
            Tuple of `torch.FloatTensor` (one for the output of the embeddings + one for the output of each layer) of
            shape `(batch_size, sequence_length, hidden_size)`.

            Hidden-states of the model at the output of each layer plus the initial embedding outputs.
        attentions (`tuple(torch.FloatTensor)`, *optional*, returned when `output_attentions=True` is passed or when `config.output_attentions=True`):
            Tuple of `torch.FloatTensor` (one for each layer) of shape `(batch_size, num_heads, sequence_length,
            sequence_length)`.

            Attentions weights after the attention softmax, used to compute the weighted average in the self-attention
            heads.
    """

    start_logits: torch.FloatTensor
    end_logits: torch.FloatTensor = None
    relevance_logits: torch.FloatTensor = None
    hidden_states: Optional[Tuple[torch.FloatTensor]] = None
    attentions: Optional[Tuple[torch.FloatTensor]] = None


class FLMRPreTrainedModel(PreTrainedModel):
    def _init_weights(self, module):
        """Initialize the weights"""
        if isinstance(module, nn.Linear):
            # Slightly different from the TF version which uses truncated_normal for initialization
            # cf https://github.com/pytorch/pytorch/pull/5617
            module.weight.data.normal_(mean=0.0, std=self.config.initializer_range)
            if module.bias is not None:
                module.bias.data.zero_()
        elif isinstance(module, nn.Embedding):
            module.weight.data.normal_(mean=0.0, std=self.config.initializer_range)
            if module.padding_idx is not None:
                module.weight.data[module.padding_idx].zero_()
        elif isinstance(module, nn.LayerNorm):
            module.bias.data.zero_()
            module.weight.data.fill_(1.0)


class FLMREncoder(FLMRPreTrainedModel):
    base_model_prefix = "bert_model"

    def __init__(self, config: FLMRConfig):
        super().__init__(config)
        self.bert_model = BertModel(config, add_pooling_layer=True)
        if self.bert_model.config.hidden_size <= 0:
            raise ValueError("Encoder hidden_size can't be zero")
        self.projection_dim = config.projection_dim
        if self.projection_dim > 0:
            self.encode_proj = nn.Linear(self.bert_model.config.hidden_size, config.projection_dim)
        # Initialize weights and apply final processing
        self.post_init()

    def forward(
        self,
        input_ids: Tensor,
        attention_mask: Optional[Tensor] = None,
        token_type_ids: Optional[Tensor] = None,
        inputs_embeds: Optional[Tensor] = None,
        output_attentions: bool = False,
        output_hidden_states: bool = False,
        return_dict: bool = False,
    ) -> Union[BaseModelOutputWithPooling, Tuple[Tensor, ...]]:
        outputs = self.bert_model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
            inputs_embeds=inputs_embeds,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
            return_dict=return_dict,
        )
        sequence_output = outputs[0]
        pooled_output = sequence_output[:, 0, :]

        if self.projection_dim > 0:
            pooled_output = self.encode_proj(pooled_output)

        if not return_dict:
            return (sequence_output, pooled_output) + outputs[2:]

        return BaseModelOutputWithPooling(
            last_hidden_state=sequence_output,
            pooler_output=pooled_output,
            hidden_states=outputs.hidden_states,
            attentions=outputs.attentions,
        )

    @property
    def embeddings_size(self) -> int:
        if self.projection_dim > 0:
            return self.encode_proj.out_features
        return self.bert_model.config.hidden_size


class FLMRSpanPredictor(FLMRPreTrainedModel):
    base_model_prefix = "encoder"

    def __init__(self, config: FLMRConfig):
        super().__init__(config)
        self.encoder = FLMREncoder(config)
        self.qa_outputs = nn.Linear(self.encoder.embeddings_size, 2)
        self.qa_classifier = nn.Linear(self.encoder.embeddings_size, 1)
        # Initialize weights and apply final processing
        self.post_init()

    def forward(
        self,
        input_ids: Tensor,
        attention_mask: Tensor,
        inputs_embeds: Optional[Tensor] = None,
        output_attentions: bool = False,
        output_hidden_states: bool = False,
        return_dict: bool = False,
    ) -> Union[FLMRReaderOutput, Tuple[Tensor, ...]]:
        # notations: N - number of questions in a batch, M - number of passages per questions, L - sequence length
        n_passages, sequence_length = input_ids.size() if input_ids is not None else inputs_embeds.size()[:2]
        # feed encoder
        outputs = self.encoder(
            input_ids,
            attention_mask=attention_mask,
            inputs_embeds=inputs_embeds,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
            return_dict=return_dict,
        )
        sequence_output = outputs[0]

        # compute logits
        logits = self.qa_outputs(sequence_output)
        start_logits, end_logits = logits.split(1, dim=-1)
        start_logits = start_logits.squeeze(-1).contiguous()
        end_logits = end_logits.squeeze(-1).contiguous()
        relevance_logits = self.qa_classifier(sequence_output[:, 0, :])

        # resize
        start_logits = start_logits.view(n_passages, sequence_length)
        end_logits = end_logits.view(n_passages, sequence_length)
        relevance_logits = relevance_logits.view(n_passages)

        if not return_dict:
            return (start_logits, end_logits, relevance_logits) + outputs[2:]

        return FLMRReaderOutput(
            start_logits=start_logits,
            end_logits=end_logits,
            relevance_logits=relevance_logits,
            hidden_states=outputs.hidden_states,
            attentions=outputs.attentions,
        )


##################
# PreTrainedModel
##################


class FLMRPretrainedModelForRetrieval(FLMRPreTrainedModel):
    """
    An abstract class to handle weights initialization and a simple interface for downloading and loading pretrained
    models.
    """

    config_class = FLMRConfig
    load_tf_weights = None
    base_model_prefix = "flmr_encoder"

class FLMRPretrainedContextEncoder(FLMRPreTrainedModel):
    """
    An abstract class to handle weights initialization and a simple interface for downloading and loading pretrained
    models.
    """

    config_class = FLMRConfig
    load_tf_weights = None
    base_model_prefix = "ctx_encoder"


class FLMRPretrainedQuestionEncoder(FLMRPreTrainedModel):
    """
    An abstract class to handle weights initialization and a simple interface for downloading and loading pretrained
    models.
    """

    config_class = FLMRConfig
    load_tf_weights = None
    base_model_prefix = "question_encoder"


class FLMRPretrainedReader(FLMRPreTrainedModel):
    """
    An abstract class to handle weights initialization and a simple interface for downloading and loading pretrained
    models.
    """

    config_class = FLMRConfig
    load_tf_weights = None
    base_model_prefix = "span_predictor"


###############
# Actual Models
###############


FLMR_START_DOCSTRING = r"""

    This model inherits from [`PreTrainedModel`]. Check the superclass documentation for the generic methods the
    library implements for all its model (such as downloading or saving, resizing the input embeddings, pruning heads
    etc.)

    This model is also a PyTorch [torch.nn.Module](https://pytorch.org/docs/stable/nn.html#torch.nn.Module) subclass.
    Use it as a regular PyTorch Module and refer to the PyTorch documentation for all matter related to general usage
    and behavior.

    Parameters:
        config ([`FLMRConfig`]): Model configuration class with all the parameters of the model.
            Initializing with a config file does not load the weights associated with the model, only the
            configuration. Check out the [`~PreTrainedModel.from_pretrained`] method to load the model weights.
"""

FLMR_ENCODERS_INPUTS_DOCSTRING = r"""
    Args:
        input_ids (`torch.LongTensor` of shape `(batch_size, sequence_length)`):
            Indices of input sequence tokens in the vocabulary. To match pretraining, FLMR input sequence should be
            formatted with [CLS] and [SEP] tokens as follows:

            (a) For sequence pairs (for a pair title+text for example):

            ```
            tokens:         [CLS] is this jack ##son ##ville ? [SEP] no it is not . [SEP]
            token_type_ids:   0   0  0    0    0     0       0   0   1  1  1  1   1   1
            ```

            (b) For single sequences (for a question for example):

            ```
            tokens:         [CLS] the dog is hairy . [SEP]
            token_type_ids:   0   0   0   0  0     0   0
            ```

            FLMR is a model with absolute position embeddings so it's usually advised to pad the inputs on the right
            rather than the left.

            Indices can be obtained using [`AutoTokenizer`]. See [`PreTrainedTokenizer.encode`] and
            [`PreTrainedTokenizer.__call__`] for details.

            [What are input IDs?](../glossary#input-ids)
        attention_mask (`torch.FloatTensor` of shape `(batch_size, sequence_length)`, *optional*):
            Mask to avoid performing attention on padding token indices. Mask values selected in `[0, 1]`:

            - 1 for tokens that are **not masked**,
            - 0 for tokens that are **masked**.

            [What are attention masks?](../glossary#attention-mask)
        token_type_ids (`torch.LongTensor` of shape `(batch_size, sequence_length)`, *optional*):
            Segment token indices to indicate first and second portions of the inputs. Indices are selected in `[0,
            1]`:

            - 0 corresponds to a *sentence A* token,
            - 1 corresponds to a *sentence B* token.

            [What are token type IDs?](../glossary#token-type-ids)
        inputs_embeds (`torch.FloatTensor` of shape `(batch_size, sequence_length, hidden_size)`, *optional*):
            Optionally, instead of passing `input_ids` you can choose to directly pass an embedded representation. This
            is useful if you want more control over how to convert `input_ids` indices into associated vectors than the
            model's internal embedding lookup matrix.
        output_attentions (`bool`, *optional*):
            Whether or not to return the attentions tensors of all attention layers. See `attentions` under returned
            tensors for more detail.
        output_hidden_states (`bool`, *optional*):
            Whether or not to return the hidden states of all layers. See `hidden_states` under returned tensors for
            more detail.
        return_dict (`bool`, *optional*):
            Whether or not to return a [`~utils.ModelOutput`] instead of a plain tuple.
"""

FLMR_READER_INPUTS_DOCSTRING = r"""
    Args:
        input_ids (`Tuple[torch.LongTensor]` of shapes `(n_passages, sequence_length)`):
            Indices of input sequence tokens in the vocabulary. It has to be a sequence triplet with 1) the question
            and 2) the passages titles and 3) the passages texts To match pretraining, FLMR `input_ids` sequence should
            be formatted with [CLS] and [SEP] with the format:

                `[CLS] <question token ids> [SEP] <titles ids> [SEP] <texts ids>`

            FLMR is a model with absolute position embeddings so it's usually advised to pad the inputs on the right
            rather than the left.

            Indices can be obtained using [`FLMRReaderTokenizer`]. See this class documentation for more details.

            [What are input IDs?](../glossary#input-ids)
        attention_mask (`torch.FloatTensor` of shape `(n_passages, sequence_length)`, *optional*):
            Mask to avoid performing attention on padding token indices. Mask values selected in `[0, 1]`:

            - 1 for tokens that are **not masked**,
            - 0 for tokens that are **masked**.

            [What are attention masks?](../glossary#attention-mask)
        inputs_embeds (`torch.FloatTensor` of shape `(n_passages, sequence_length, hidden_size)`, *optional*):
            Optionally, instead of passing `input_ids` you can choose to directly pass an embedded representation. This
            is useful if you want more control over how to convert `input_ids` indices into associated vectors than the
            model's internal embedding lookup matrix.
        output_attentions (`bool`, *optional*):
            Whether or not to return the attentions tensors of all attention layers. See `attentions` under returned
            tensors for more detail.
        output_hidden_states (`bool`, *optional*):
            Whether or not to return the hidden states of all layers. See `hidden_states` under returned tensors for
            more detail.
        return_dict (`bool`, *optional*):
            Whether or not to return a [`~utils.ModelOutput`] instead of a plain tuple.
"""


from colbert.infra.config.config import ColBERTConfig
from colbert.search.strided_tensor import StridedTensor
from colbert.utils.utils import print_message, flatten
from colbert.modeling.base_colbert import BaseColBERT
from transformers import AutoTokenizer

import torch
import string

import os
import pathlib
from torch.utils.cpp_extension import load
import torch.distributed as dist
from tqdm import tqdm

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


def colbert_score_packed(Q, D_packed, D_lengths, config=ColBERTConfig()):
    """
        Works with a single query only.
    """

    use_gpu = config.total_visible_gpus > 0

    if use_gpu:
        Q, D_packed, D_lengths = Q.cuda(), D_packed.cuda(), D_lengths.cuda()

    Q = Q.squeeze(0)

    assert Q.dim() == 2, Q.size()
    assert D_packed.dim() == 2, D_packed.size()

    scores = D_packed @ Q.to(dtype=D_packed.dtype).T

    if use_gpu or config.interaction == "flipr":
        scores_padded, scores_mask = StridedTensor(scores, D_lengths, use_gpu=use_gpu).as_padded_tensor()

        return colbert_score_reduce(scores_padded, scores_mask, config)
    else:
        return FLMRModelForRetrieval.segmented_maxsim(scores, D_lengths)



def _stack_3D_tensors(groups):
    bsize = sum([x.size(0) for x in groups])
    maxlen = max([x.size(1) for x in groups])
    hdim = groups[0].size(2)

    output = torch.zeros(bsize, maxlen, hdim, device=groups[0].device, dtype=groups[0].dtype)

    offset = 0
    for x in groups:
        endpos = offset + x.size(0)
        output[offset:endpos, :x.size(1)] = x
        offset = endpos

    return output


class MLP(nn.Module):
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.model(x)

    def __init__(self, sizes, bias=True, act=nn.Tanh):
        super(MLP, self).__init__()
        layers = []
        for i in range(len(sizes) - 1):
            layers.append(nn.Linear(sizes[i], sizes[i + 1], bias=bias))
            if i < len(sizes) - 2:
                layers.append(act())
        self.model = nn.Sequential(*layers)

from transformers import AutoConfig, AutoModel
import copy
import importlib

@add_start_docstrings(
    "The bare FLMRQuestionEncoder transformer outputting pooler outputs as question representations.",
    FLMR_START_DOCSTRING,
)
class FLMRModelForRetrieval(FLMRPretrainedModelForRetrieval):
    _keys_to_ignore_on_load_unexpected = [r"cls"]
    
    def __init__(
            self, 
            config: FLMRConfig, 
            query_tokenizer=None, 
            context_tokenizer=None
        ):
        super().__init__(config)
        self.config = config

        self.context_text_encoder = FLMREncoder(config)
        self.context_text_encoder_linear = nn.Linear(config.hidden_size, config.dim, bias=False)

        self.query_tokenizer = query_tokenizer
        self.context_tokenizer = context_tokenizer


        self.mapping_network_prefix_length = self.config.mapping_network_prefix_length
        self.vision_encoder_embedding_size = self.config.vision_encoder_dim
        self.text_encoder_embedding_size = self.config.dim
        
        self.context_vision_projection = MLP(
            (
                self.vision_encoder_embedding_size,
                (self.text_encoder_embedding_size * self.mapping_network_prefix_length) // 2,
                self.text_encoder_embedding_size * self.mapping_network_prefix_length,
            )
        )

        if self.config.use_vision_encoder:
            # self.vision_model_config_class = self.config.vision_model_config_class
            # self.vision_model_class = self.config.vision_model_class
            self.vision_model_version = self.config.vision_model_version

            try:
                from transformers import CLIPVisionConfig, CLIPVisionModel
            except:
                raise ImportError("Failed to import CLIPVisionConfig and CLIPVisionModel from transformers. ")

            vision_model_config = CLIPVisionConfig.from_pretrained(self.vision_model_version)
            self.context_vision_encoder = CLIPVisionModel.from_pretrained(self.vision_model_version, config=vision_model_config)
        
        if self.config.separate_query_and_context_text_encoder:
            self.query_text_encoder = copy.deepcopy(self.context_text_encoder)
            self.query_text_encoder_linear = copy.deepcopy(self.context_text_encoder_linear)
        else:
            self.query_text_encoder = self.context_text_encoder
            self.query_text_encoder_linear = self.context_text_encoder_linear

        if self.config.separate_query_and_context_vision_encoder:
            self.query_vision_encoder = copy.deepcopy(self.context_vision_encoder)
            self.query_vision_projection = copy.deepcopy(self.context_vision_projection)
        else:
            self.query_vision_encoder = self.context_vision_encoder
            self.query_vision_projection = self.context_vision_projection

        self.use_gpu = True

        FLMRModelForRetrieval.try_load_torch_extensions(self.use_gpu)

        if self.config.mask_punctuation:
            self.skiplist = {w: True
                             for symbol in string.punctuation
                             for w in [symbol, self.context_tokenizer.encode(symbol, add_special_tokens=False)[0]]}
        self.loss_fn = torch.nn.CrossEntropyLoss()

        # Initialize weights and apply final processing
        self.post_init()

    @classmethod
    def from_pretrained(self, name_or_path, **kwargs):
        obj = super().from_pretrained(name_or_path, **kwargs)
        return obj


    @classmethod
    def try_load_torch_extensions(cls, use_gpu):
        if hasattr(cls, "loaded_extensions") or use_gpu:
            return

        print_message(f"Loading segmented_maxsim_cpp extension (set COLBERT_LOAD_TORCH_EXTENSION_VERBOSE=True for more info)...")
        segmented_maxsim_cpp = load(
            name="segmented_maxsim_cpp",
            sources=[
                os.path.join(
                    pathlib.Path(__file__).parent.resolve(), "segmented_maxsim.cpp"
                ),
            ],
            extra_cflags=["-O3"],
            verbose=os.getenv("COLBERT_LOAD_TORCH_EXTENSION_VERBOSE", "False") == "True",
        )
        cls.segmented_maxsim = segmented_maxsim_cpp.segmented_maxsim_cpp

        cls.loaded_extensions = True

    def forward(
            self, 
            query_input_ids: Optional[torch.Tensor]=None,
            query_attention_mask: Optional[torch.Tensor]=None,
            query_pixel_values: Optional[torch.Tensor]=None,
            query_image_features: Optional[torch.Tensor]=None,
            context_input_ids: Optional[torch.Tensor]=None,
            context_attention_mask: Optional[torch.Tensor]=None,
            context_pixel_values: Optional[torch.Tensor] = None,
            context_image_features: Optional[torch.Tensor] = None,
            use_in_batch_negatives: bool = True,
            in_batch_negatives_from_all_gpus: bool = False, 
            num_negative_examples: int = 1,
            query_concat_output_from_vision_encoder: Optional[bool] = None,
            query_concat_output_from_text_encoder: Optional[bool] = None,
            context_concat_output_from_vision_encoder: Optional[bool] = None,
            context_concat_output_from_text_encoder: Optional[bool] = None,
        ):

        if query_concat_output_from_vision_encoder is None:
            query_concat_output_from_vision_encoder = self.config.query_concat_output_from_vision_encoder
        
        if query_concat_output_from_text_encoder is None:
            query_concat_output_from_text_encoder = self.config.query_concat_output_from_text_encoder
        
        if context_concat_output_from_vision_encoder is None:
            context_concat_output_from_vision_encoder = self.config.context_concat_output_from_vision_encoder

        if context_concat_output_from_text_encoder is None:
            context_concat_output_from_text_encoder = self.config.context_concat_output_from_text_encoder
        
        query_outputs = self.query(
            input_ids=query_input_ids, 
            attention_mask=query_attention_mask,
            pixel_values=query_pixel_values,
            image_features=query_image_features,
            # input_modality=query_input_modality,
            concat_output_from_vision_encoder=query_concat_output_from_vision_encoder,
            concat_output_from_text_encoder=query_concat_output_from_text_encoder,
        )
        Q = query_outputs.late_interaction_output

        context_outputs = self.doc(
            input_ids=context_input_ids,
            attention_mask=context_attention_mask,
            pixel_values=context_pixel_values,
            image_features=context_image_features,
            # input_modality=context_input_modality,
            concat_output_from_vision_encoder=context_concat_output_from_vision_encoder,
            concat_output_from_text_encoder=context_concat_output_from_text_encoder,
            keep_dims='return_mask'
        )
        D, D_mask = context_outputs.late_interaction_output, context_outputs.context_mask

        print(Q.shape, D.shape, D_mask.shape)

        # Gather tensors from other GPUs
        if in_batch_negatives_from_all_gpus:
            Q, D, D_mask = self.gather_tensors_from_other_gpus(Q, D, D_mask)
        # Repeat each query encoding for every corresponding document.
        Q_duplicated = Q.repeat_interleave(num_negative_examples+1, dim=0).contiguous()

        scores = self.score(Q_duplicated, D, D_mask)

        if use_in_batch_negatives:
            ib_loss = self.compute_ib_loss_new(Q, D, D_mask)
            return scores, ib_loss

        return scores
    
    def compute_ib_loss_new(self, Q, D, D_mask):
        # Q: batch_size x q_len x dim
        # D: batch_size*n_docs x i_len x dim
        # D_mask: batch_size*n_docs x i_len x dim
        # 1 x batch_size*n_docs x i_len x dim matmul batch_size x 1 x q_len x dim
        # = batch_size x batch_size*n_docs x i_len x q_len

        scores = (D.float().unsqueeze(0) @ Q.float().permute(0, 2, 1).unsqueeze(1)).flatten(0, 1)  # query-major unsqueeze
        scores = colbert_score_reduce(scores, D_mask.repeat(Q.size(0), 1, 1))
        
        in_batch_scores = scores.reshape(Q.size(0), -1)
        # print('in_batch_scores', in_batch_scores.shape, in_batch_scores)

        batch_size = Q.shape[0]
        batch_size_with_pos_and_neg = D.shape[0]
        num_pos_and_neg = batch_size_with_pos_and_neg // batch_size
        num_pos = 1
        num_neg = num_pos_and_neg - num_pos
        
        # batch_size x dim  matmul  dim x (num_pos+num_neg)*batch_size  
        # -->  batch_size x (num_pos+num_neg)*batch_size
        in_batch_labels = torch.zeros(batch_size, batch_size_with_pos_and_neg).to(scores.device)
        step = num_pos_and_neg
        for i in range(batch_size):
            in_batch_labels[i, step*i] = 1
        # print('in_batch_labels', in_batch_labels)
        in_batch_labels = torch.argmax(in_batch_labels, dim=1)
        # print('in_batch_labels', in_batch_labels)
        
        loss = self.loss_fn(in_batch_scores, in_batch_labels)

        return loss

    def gather_tensors_from_other_gpus(self, query_embeddings, item_embeddings, item_mask):
        # print("get rank", get_rank())
        # print("get world size", get_world_size())
        # Gather embeddings from other GPUs
        n_nodes = get_world_size()
        if n_nodes == 1:
            return query_embeddings, item_embeddings, item_mask
        # Create placeholder to hold embeddings passed from other ranks
        global_query_embeddings_placeholder = [torch.zeros(*query_embeddings.shape, dtype=query_embeddings.dtype).to(query_embeddings.device) for _ in range(n_nodes)]
        global_item_embeddings_placeholder = [torch.zeros(*item_embeddings.shape, dtype=item_embeddings.dtype).to(item_embeddings.device) for _ in range(n_nodes)]
        global_item_mask_placeholder = [torch.zeros(*item_mask.shape, dtype=item_mask.dtype).to(item_mask.device) for _ in range(n_nodes)]
        dist.all_gather(global_query_embeddings_placeholder, query_embeddings.detach())
        dist.all_gather(global_item_embeddings_placeholder, item_embeddings.detach())
        dist.all_gather(global_item_mask_placeholder, item_mask.detach())

        global_query_embeddings = []
        global_item_embeddings = []
        global_item_mask = []
        # print(f"rank {get_rank()} global_query_embeddings", global_query_embeddings)
        # print(f"rank {get_rank()} global_item_embeddings", global_item_embeddings)
        # input()
        current_rank = get_rank()
        for rank_index, remote_q_embeddings in enumerate(global_query_embeddings_placeholder):
            # We append the embeddings from other GPUs if this embedding does not require gradients
            if rank_index != current_rank:
                global_query_embeddings.append(remote_q_embeddings)
            else:
                global_query_embeddings.append(query_embeddings)

        for rank_index, remote_item_embeddings in enumerate(global_item_embeddings_placeholder):
            # We append the embeddings from other GPUs if this embedding does not require gradients
            if rank_index != current_rank:
                global_item_embeddings.append(remote_item_embeddings)
            else:
                global_item_embeddings.append(item_embeddings)
        
        for rank_index, remote_item_mask in enumerate(global_item_mask_placeholder):
            # We append the embeddings from other GPUs if this embedding does not require gradients
            if rank_index != current_rank:
                global_item_mask.append(remote_item_mask)
            else:
                global_item_mask.append(item_mask)

        # Replace the previous variables with gathered tensors
        query_embeddings = torch.cat(global_query_embeddings)
        item_embeddings = torch.cat(global_item_embeddings)
        item_mask = torch.cat(global_item_mask)

        return query_embeddings, item_embeddings, item_mask

    
    def query(
            self, 
            input_ids: torch.Tensor,
            attention_mask: torch.Tensor, 
            pixel_values: Optional[torch.Tensor] = None,
            image_features: Optional[torch.Tensor] = None,
            # input_modality: Optional[List[str]] = ['text', 'image'],
            concat_output_from_vision_encoder: Optional[bool] = None,
            concat_output_from_text_encoder: Optional[bool] = None,
        ):

        if concat_output_from_vision_encoder is None:
            concat_output_from_vision_encoder = self.config.query_concat_output_from_vision_encoder
        
        if concat_output_from_text_encoder is None:
            concat_output_from_text_encoder = self.config.query_concat_output_from_text_encoder

        input_modality = []
        if pixel_values is not None or image_features is not None:
            input_modality.append('image')
        if input_ids is not None and attention_mask is not None:
            input_modality.append('text')
        
        if 'image' in input_modality:
            assert pixel_values is not None or image_features is not None, "pixel_values or image_features must be provided if image modality is used"
            assert pixel_values is None or image_features is None, "pixel_values and image_features cannot be provided at the same time"
        
        if 'text' in input_modality:
            assert input_ids is not None and attention_mask is not None, "input_ids and attention_mask must be provided if text modality is used"
            # Forward the text encoder
            input_ids, attention_mask = input_ids.to(self.device), attention_mask.to(self.device)
            text_embeddings = self.query_text_encoder(input_ids, attention_mask=attention_mask)[0]
            text_embeddings = self.query_text_encoder_linear(text_embeddings)

            mask = torch.tensor(self.mask(input_ids, skiplist=[]), device=self.device).unsqueeze(2).float()
            text_embeddings = text_embeddings * mask

        if 'image' in input_modality:
            if pixel_values is not None:
                # Forward the vision encoder
                pixel_values = pixel_values.to(self.device)
                outputs = self.query_vision_encoder(pixel_values)
                vision_embeddings = outputs.last_hidden_state[:, 0]
            
            if image_features is not None:
                vision_embeddings = image_features.to(self.device)
            
            batch_size = vision_embeddings.shape[0]
            
            # Forward the vision projection / mapping network
            vision_embeddings = self.query_vision_projection(vision_embeddings)
            vision_embeddings = vision_embeddings.view(
                -1, self.mapping_network_prefix_length, self.text_encoder_embedding_size
            )

        if concat_output_from_vision_encoder and concat_output_from_text_encoder:
            Q = torch.cat([vision_embeddings, text_embeddings], dim=1)
        elif concat_output_from_vision_encoder:
            Q = vision_embeddings
        elif concat_output_from_text_encoder:
            Q = text_embeddings

        return FLMRQuestionEncoderOutput(
            pooler_output=Q[:, 0, :],
            late_interaction_output=torch.nn.functional.normalize(Q, p=2, dim=2),
        )

    def doc(
            self, 
            input_ids: torch.Tensor,
            attention_mask: torch.Tensor, 
            pixel_values: Optional[torch.Tensor] = None,
            image_features: Optional[torch.Tensor] = None,
            # input_modality: Optional[List[str]] = ['text', 'image'],
            concat_output_from_vision_encoder: Optional[bool] = None,
            concat_output_from_text_encoder: Optional[bool] = None,
            keep_dims: Optional[bool] = True,
            return_mask: Optional[bool] = True,
        ):
        
        assert keep_dims in [True, False, 'return_mask']

        if concat_output_from_vision_encoder is None:
            concat_output_from_vision_encoder = self.config.context_concat_output_from_vision_encoder
        
        if concat_output_from_text_encoder is None:
            concat_output_from_text_encoder = self.config.context_concat_output_from_text_encoder
        
        input_modality = []
        if pixel_values is not None or image_features is not None:
            input_modality.append('image')
        if input_ids is not None and attention_mask is not None:
            input_modality.append('text')

        if 'image' in input_modality:
            assert pixel_values is not None or image_features is not None, "pixel_values or image_features must be provided if image modality is used"
            assert pixel_values is None or image_features is None, "pixel_values and image_features cannot be provided at the same time"
        
        if 'text' in input_modality:
            assert input_ids is not None and attention_mask is not None, "input_ids and attention_mask must be provided if text modality is used"
            # Forward the text encoder
            input_ids, attention_mask = input_ids.to(self.device), attention_mask.to(self.device)
            text_embeddings = self.context_text_encoder(input_ids, attention_mask=attention_mask)[0]
            text_embeddings = self.context_text_encoder_linear(text_embeddings)

            mask = torch.tensor(self.mask(input_ids, skiplist=self.skiplist), device=self.device).unsqueeze(2).float()
            text_embeddings = text_embeddings * mask

        if 'image' in input_modality:
            if pixel_values is not None:
                # Forward the vision encoder
                pixel_values = pixel_values.to(self.device)
                outputs = self.context_vision_encoder(pixel_values)
                vision_embeddings = outputs.last_hidden_state[:, 0]
            
            if image_features is not None:
                vision_embeddings = image_features.to(self.device)
            
            batch_size = vision_embeddings.shape[0]
            
            # Forward the vision projection / mapping network
            vision_embeddings = self.context_vision_projection(vision_embeddings)
            vision_embeddings = vision_embeddings.view(
                -1, self.mapping_network_prefix_length, self.text_encoder_embedding_size
            )

            image_mask = torch.ones(batch_size, vision_embeddings.shape[1], 1).to(self.device)

        if concat_output_from_vision_encoder and concat_output_from_text_encoder:
            # Note: vision embeddings must be in the front since the ColBERT engine only indexes embeddings up to number of 1's in the mask
            # TODO: fix the engine to support masks with discontinuous 0 and 1.
            D = torch.cat([vision_embeddings, text_embeddings], dim=1)
            # concatenate the mask
            mask = torch.cat([mask, image_mask], dim=1)
        elif concat_output_from_vision_encoder:
            D = vision_embeddings
            mask = image_mask
        elif concat_output_from_text_encoder:
            D = text_embeddings
            mask = mask

        D = torch.nn.functional.normalize(D, p=2, dim=2)

        if self.use_gpu:
            D = D.half()

        if keep_dims is False:
            D, mask = D.cpu(), mask.bool().cpu().squeeze(-1)
            D = [d[mask[idx]] for idx, d in enumerate(D)]

        return FLMRContextEncoderOutput(
            pooler_output=D[:, 0, :],
            late_interaction_output=D,
            context_mask=mask.bool() if return_mask else None,
        )

    def score(self, Q, D_padded, D_mask):
        # assert self.colbert_config.similarity == 'cosine'
        # if self.colbert_config.similarity == 'l2':
        #     assert self.colbert_config.interaction == 'colbert'
        #     return (-1.0 * ((Q.unsqueeze(2) - D_padded.unsqueeze(1))**2).sum(-1)).max(-1).values.sum(-1)
        return colbert_score(Q, D_padded, D_mask, use_gpu=self.use_gpu)

    def mask(self, input_ids, skiplist):
        mask = [[(x not in skiplist) and (x != 0) for x in d] for d in input_ids.cpu().tolist()]
        return mask
    

    # @add_start_docstrings_to_model_forward(FLMR_ENCODERS_INPUTS_DOCSTRING)
    # @replace_return_docstrings(output_type=FLMRQuestionEncoderOutput, config_class=_CONFIG_FOR_DOC)
    # def forward(
    #     self,
    #     input_ids: Optional[Tensor] = None,
    #     attention_mask: Optional[Tensor] = None,
    #     token_type_ids: Optional[Tensor] = None,
    #     inputs_embeds: Optional[Tensor] = None,
    #     output_attentions: Optional[bool] = None,
    #     output_hidden_states: Optional[bool] = None,
    #     return_dict: Optional[bool] = None,
    # ) -> Union[FLMRQuestionEncoderOutput, Tuple[Tensor, ...]]:
    #     r"""
    #     Return:

    #     Examples:

    #     ```python
    #     >>> from transformers import FLMRQuestionEncoder, FLMRTokenizer

    #     >>> tokenizer = FLMRTokenizer.from_pretrained("facebook/flmr-question_encoder-single-nq-base")
    #     >>> model = FLMRQuestionEncoder.from_pretrained("facebook/flmr-question_encoder-single-nq-base")
    #     >>> input_ids = tokenizer("Hello, is my dog cute ?", return_tensors="pt")["input_ids"]
    #     >>> embeddings = model(input_ids).pooler_output
    #     ```
    #     """
    #     output_attentions = output_attentions if output_attentions is not None else self.config.output_attentions
    #     output_hidden_states = (
    #         output_hidden_states if output_hidden_states is not None else self.config.output_hidden_states
    #     )
    #     return_dict = return_dict if return_dict is not None else self.config.use_return_dict

    #     if input_ids is not None and inputs_embeds is not None:
    #         raise ValueError("You cannot specify both input_ids and inputs_embeds at the same time")
    #     elif input_ids is not None:
    #         self.warn_if_padding_and_no_attention_mask(input_ids, attention_mask)
    #         input_shape = input_ids.size()
    #     elif inputs_embeds is not None:
    #         input_shape = inputs_embeds.size()[:-1]
    #     else:
    #         raise ValueError("You have to specify either input_ids or inputs_embeds")

    #     device = input_ids.device if input_ids is not None else inputs_embeds.device

    #     if attention_mask is None:
    #         attention_mask = (
    #             torch.ones(input_shape, device=device)
    #             if input_ids is None
    #             else (input_ids != self.config.pad_token_id)
    #         )
    #     if token_type_ids is None:
    #         token_type_ids = torch.zeros(input_shape, dtype=torch.long, device=device)

    #     outputs = self.text_encoder(
    #         input_ids=input_ids,
    #         attention_mask=attention_mask,
    #         token_type_ids=token_type_ids,
    #         inputs_embeds=inputs_embeds,
    #         output_attentions=output_attentions,
    #         output_hidden_states=output_hidden_states,
    #         return_dict=return_dict,
    #     )

    #     if not return_dict:
    #         return outputs[1:]
    #     return FLMRQuestionEncoderOutput(
    #         pooler_output=outputs.pooler_output, hidden_states=outputs.hidden_states, attentions=outputs.attentions
    #     )



import numpy as np
from colbert.utils.amp import MixedPrecisionManager
from colbert.modeling.tokenization.utils import _split_into_batches, _sort_by_length
from transformers import AutoImageProcessor
from PIL import Image

class FLMRModelForIndexing(FLMRModelForRetrieval):
    
    def __init__(
            self, config: FLMRConfig, 
            **kwargs,
        ):
        super().__init__(config, **kwargs)
        self.amp_manager = MixedPrecisionManager(True)
        self.image_processor = AutoImageProcessor.from_pretrained(self.config.vision_model_version)
    
    def query(self, *args, to_cpu=False, **kw_args):
        with torch.no_grad():
            with self.amp_manager.context():
                Q = super().query(*args, **kw_args)
                return Q.cpu() if to_cpu else Q

    def doc(self, *args, to_cpu=False, **kw_args):
        with torch.no_grad():
            with self.amp_manager.context():
                D = super().doc(*args, **kw_args)

                if to_cpu:
                    return (D[0].cpu(), *D[1:]) if isinstance(D, tuple) else D.cpu()

                return D

    def queryFromText(self, queries, bsize=None, to_cpu=False, context=None):
        if bsize:
            batches = self.query_tokenizer(queries, context=context, bsize=bsize)
            batches = [self.query(input_ids, attention_mask, to_cpu=to_cpu) for input_ids, attention_mask in batches]
            batches = [b.late_interaction_output for b in batches]
            return torch.cat(batches)

        input_ids, attention_mask = self.query_tokenizer(queries, context=context)
        return self.query(input_ids, attention_mask)

    def docFromText(self, docs, bsize=None, keep_dims=True, to_cpu=False, showprogress=False, return_tokens=False):
        assert keep_dims in [True, False, 'flatten']

        # docs can be
        # (1) list of text
        # (2) list of tuples (text, image_features, None)
        # (3) list of tuples (text, None, image_paths)

        if isinstance(docs[0], tuple):
            texts = []
            image_features = []
            image_paths = []
            for doc in docs:
                text, image_feature, image_path = doc
                texts.append(text)
                image_features.append(image_feature)
                image_paths.append(image_path)
            
            docs = texts
            if image_features[0] is not None:
                image_features = torch.FloatTensor(np.stack(image_features))
                is_input_image_features = True
            else:
                is_input_image_features = False

            multimodal_docs = True
        else:
            image_features = None
            image_paths = None
            multimodal_docs = False

        if bsize:
            # we change this part to enable dynamically loading image features to avoid memory overflow
            # This bsize function is used in the original ColBERT codebase to split inputs into multiple batches
            context_encoding = self.context_tokenizer(docs)
            ids, mask = context_encoding['input_ids'], context_encoding['attention_mask']

            if multimodal_docs:
                # print(ids[0], mask[0], image_features[0], image_paths[0])
                # print(image_features.shape)
                ids, mask, image_features, image_paths, reverse_indices = _sort_by_length(ids, mask, bsize, image_features, image_paths)
                # print(image_features.shape)
                # print(len(ids), len(mask), len(image_features), len(image_paths))
                # print(ids[0], mask[0], image_features[0], image_paths[0])
                batches = _split_into_batches(ids, mask, bsize, image_features, image_paths)
            else:
                ids, mask, reverse_indices = _sort_by_length(ids, mask, bsize)
                batches = _split_into_batches(ids, mask, bsize)

            # text_batches, reverse_indices = self.context_tokenizer(docs, bsize=bsize)
            
            returned_text = []
            if return_tokens:
                text_batches = [(input_ids, attention_mask) for input_ids, attention_mask, _, _ in batches]
                returned_text = [text for batch in text_batches for text in batch[0]]
                returned_text = [returned_text[idx] for idx in reverse_indices.tolist()]
                returned_text = [returned_text]
            
            
            keep_dims_ = 'return_mask' if keep_dims == 'flatten' else keep_dims
            return_mask = True if keep_dims == 'flatten' else False

            encoded_batches = []

            for batch in tqdm(batches, disable=not showprogress):
                if multimodal_docs:
                    input_ids, attention_mask, image_features, image_paths = batch
                    if is_input_image_features:
                        context_output = self.doc(
                            input_ids=input_ids, 
                            attention_mask=attention_mask, 
                            image_features=image_features,
                            keep_dims=keep_dims_, 
                            return_mask=return_mask, 
                            to_cpu=to_cpu,
                        )
                    else:
                        # Open the images in image_paths and convert to pixel_values by using ImageProcessor
                        images = [Image.open(image_path).convert("RGB") for image_path in image_paths]
                        pixel_values = self.image_processor(images, return_tensors="pt").pixel_values
                        print(pixel_values.shape)
                        context_output = self.doc(
                            input_ids, 
                            attention_mask, 
                            pixel_values=pixel_values, 
                            keep_dims=keep_dims_, 
                            return_mask=return_mask, 
                            to_cpu=to_cpu,
                        )
                else:
                    input_ids, attention_mask = batch
                    context_output = self.doc(
                        input_ids=input_ids,
                        attention_mask=attention_mask,
                        keep_dims=keep_dims_, 
                        return_mask=return_mask, 
                        to_cpu=to_cpu,
                    )
                
                encoded_batches.append(context_output)
                
            
            if keep_dims is True:
                D = _stack_3D_tensors(batches)
                return (D[reverse_indices], *returned_text)

            elif keep_dims == 'flatten':
                D, mask = [], []

                for batch in encoded_batches:
                    D_, mask_ = batch.late_interaction_output, batch.context_mask
                    D.append(D_)
                    mask.append(mask_)

                D, mask = torch.cat(D)[reverse_indices], torch.cat(mask)[reverse_indices]
                print(D)
                print(mask)

                doclens = mask.squeeze(-1).sum(-1).tolist()
                print("doclens",   doclens)

                D = D.view(-1, self.config.dim)
                D = D[mask.bool().flatten()].cpu()

                return (D, doclens, *returned_text)

            assert keep_dims is False

            D = [d for batch in batches for d in batch]
            return ([D[idx] for idx in reverse_indices.tolist()], *returned_text)

        input_ids, attention_mask = self.context_tokenizer(docs)
        return self.doc(input_ids, attention_mask, keep_dims=keep_dims, to_cpu=to_cpu)




@add_start_docstrings(
    "The bare FLMRContextEncoder transformer outputting pooler outputs as context representations.",
    FLMR_START_DOCSTRING,
)
class FLMRContextEncoder(FLMRPretrainedContextEncoder):
    def __init__(self, config: FLMRConfig):
        super().__init__(config)
        self.config = config
        self.ctx_encoder = FLMREncoder(config)
        # Initialize weights and apply final processing
        self.post_init()

    @add_start_docstrings_to_model_forward(FLMR_ENCODERS_INPUTS_DOCSTRING)
    @replace_return_docstrings(output_type=FLMRContextEncoderOutput, config_class=_CONFIG_FOR_DOC)
    def forward(
        self,
        input_ids: Optional[Tensor] = None,
        attention_mask: Optional[Tensor] = None,
        token_type_ids: Optional[Tensor] = None,
        inputs_embeds: Optional[Tensor] = None,
        output_attentions: Optional[bool] = None,
        output_hidden_states: Optional[bool] = None,
        return_dict: Optional[bool] = None,
    ) -> Union[FLMRContextEncoderOutput, Tuple[Tensor, ...]]:
        r"""
        Return:

        Examples:

        ```python
        >>> from transformers import FLMRContextEncoder, FLMRContextEncoderTokenizer

        >>> tokenizer = FLMRContextEncoderTokenizer.from_pretrained("weizhelin/flmr")
        >>> model = FLMRContextEncoder.from_pretrained("weizhelin/flmr")
        >>> input_ids = tokenizer("Hello, is my dog cute ?", return_tensors="pt")["input_ids"]
        >>> embeddings = model(input_ids).pooler_output
        ```"""

        output_attentions = output_attentions if output_attentions is not None else self.config.output_attentions
        output_hidden_states = (
            output_hidden_states if output_hidden_states is not None else self.config.output_hidden_states
        )
        return_dict = return_dict if return_dict is not None else self.config.use_return_dict

        if input_ids is not None and inputs_embeds is not None:
            raise ValueError("You cannot specify both input_ids and inputs_embeds at the same time")
        elif input_ids is not None:
            input_shape = input_ids.size()
        elif inputs_embeds is not None:
            input_shape = inputs_embeds.size()[:-1]
        else:
            raise ValueError("You have to specify either input_ids or inputs_embeds")

        device = input_ids.device if input_ids is not None else inputs_embeds.device

        if attention_mask is None:
            attention_mask = (
                torch.ones(input_shape, device=device)
                if input_ids is None
                else (input_ids != self.config.pad_token_id)
            )
        if token_type_ids is None:
            token_type_ids = torch.zeros(input_shape, dtype=torch.long, device=device)

        outputs = self.ctx_encoder(
            input_ids=input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
            inputs_embeds=inputs_embeds,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
            return_dict=return_dict,
        )

        if not return_dict:
            return outputs[1:]
        return FLMRContextEncoderOutput(
            pooler_output=outputs.pooler_output, hidden_states=outputs.hidden_states, attentions=outputs.attentions
        )


@add_start_docstrings(
    "The bare FLMRQuestionEncoder transformer outputting pooler outputs as question representations.",
    FLMR_START_DOCSTRING,
)
class FLMRQuestionEncoder(FLMRPretrainedQuestionEncoder):
    _keys_to_ignore_on_load_unexpected = [r"cls"]
    
    def __init__(self, config: FLMRConfig):
        super().__init__(config)
        self.config = config
        # self.question_encoder = FLMREncoder(config)
        self.bert = FLMREncoder(config)
        self.linear = nn.Linear(config.hidden_size, config.dim, bias=False)

        # Initialize weights and apply final processing
        self.post_init()

    @add_start_docstrings_to_model_forward(FLMR_ENCODERS_INPUTS_DOCSTRING)
    @replace_return_docstrings(output_type=FLMRQuestionEncoderOutput, config_class=_CONFIG_FOR_DOC)
    def forward(
        self,
        input_ids: Optional[Tensor] = None,
        attention_mask: Optional[Tensor] = None,
        token_type_ids: Optional[Tensor] = None,
        inputs_embeds: Optional[Tensor] = None,
        output_attentions: Optional[bool] = None,
        output_hidden_states: Optional[bool] = None,
        return_dict: Optional[bool] = None,
    ) -> Union[FLMRQuestionEncoderOutput, Tuple[Tensor, ...]]:
        r"""
        Return:

        Examples:

        ```python
        >>> from transformers import FLMRQuestionEncoder, FLMRTokenizer

        >>> tokenizer = FLMRTokenizer.from_pretrained("facebook/flmr-question_encoder-single-nq-base")
        >>> model = FLMRQuestionEncoder.from_pretrained("facebook/flmr-question_encoder-single-nq-base")
        >>> input_ids = tokenizer("Hello, is my dog cute ?", return_tensors="pt")["input_ids"]
        >>> embeddings = model(input_ids).pooler_output
        ```
        """
        output_attentions = output_attentions if output_attentions is not None else self.config.output_attentions
        output_hidden_states = (
            output_hidden_states if output_hidden_states is not None else self.config.output_hidden_states
        )
        return_dict = return_dict if return_dict is not None else self.config.use_return_dict

        if input_ids is not None and inputs_embeds is not None:
            raise ValueError("You cannot specify both input_ids and inputs_embeds at the same time")
        elif input_ids is not None:
            self.warn_if_padding_and_no_attention_mask(input_ids, attention_mask)
            input_shape = input_ids.size()
        elif inputs_embeds is not None:
            input_shape = inputs_embeds.size()[:-1]
        else:
            raise ValueError("You have to specify either input_ids or inputs_embeds")

        device = input_ids.device if input_ids is not None else inputs_embeds.device

        if attention_mask is None:
            attention_mask = (
                torch.ones(input_shape, device=device)
                if input_ids is None
                else (input_ids != self.config.pad_token_id)
            )
        if token_type_ids is None:
            token_type_ids = torch.zeros(input_shape, dtype=torch.long, device=device)

        outputs = self.question_encoder(
            input_ids=input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
            inputs_embeds=inputs_embeds,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
            return_dict=return_dict,
        )

        if not return_dict:
            return outputs[1:]
        return FLMRQuestionEncoderOutput(
            pooler_output=outputs.pooler_output, hidden_states=outputs.hidden_states, attentions=outputs.attentions
        )


@add_start_docstrings(
    "The bare FLMRReader transformer outputting span predictions.",
    FLMR_START_DOCSTRING,
)
class FLMRReader(FLMRPretrainedReader):
    def __init__(self, config: FLMRConfig):
        super().__init__(config)
        self.config = config
        self.span_predictor = FLMRSpanPredictor(config)
        # Initialize weights and apply final processing
        self.post_init()

    @add_start_docstrings_to_model_forward(FLMR_READER_INPUTS_DOCSTRING)
    @replace_return_docstrings(output_type=FLMRReaderOutput, config_class=_CONFIG_FOR_DOC)
    def forward(
        self,
        input_ids: Optional[Tensor] = None,
        attention_mask: Optional[Tensor] = None,
        inputs_embeds: Optional[Tensor] = None,
        output_attentions: Optional[bool] = None,
        output_hidden_states: Optional[bool] = None,
        return_dict: Optional[bool] = None,
    ) -> Union[FLMRReaderOutput, Tuple[Tensor, ...]]:
        r"""
        Return:

        Examples:

        ```python
        >>> from transformers import FLMRReader, FLMRReaderTokenizer

        >>> tokenizer = FLMRReaderTokenizer.from_pretrained("facebook/flmr-reader-single-nq-base")
        >>> model = FLMRReader.from_pretrained("facebook/flmr-reader-single-nq-base")
        >>> encoded_inputs = tokenizer(
        ...     questions=["What is love ?"],
        ...     titles=["Haddaway"],
        ...     texts=["'What Is Love' is a song recorded by the artist Haddaway"],
        ...     return_tensors="pt",
        ... )
        >>> outputs = model(**encoded_inputs)
        >>> start_logits = outputs.start_logits
        >>> end_logits = outputs.end_logits
        >>> relevance_logits = outputs.relevance_logits
        ```
        """
        output_attentions = output_attentions if output_attentions is not None else self.config.output_attentions
        output_hidden_states = (
            output_hidden_states if output_hidden_states is not None else self.config.output_hidden_states
        )
        return_dict = return_dict if return_dict is not None else self.config.use_return_dict

        if input_ids is not None and inputs_embeds is not None:
            raise ValueError("You cannot specify both input_ids and inputs_embeds at the same time")
        elif input_ids is not None:
            self.warn_if_padding_and_no_attention_mask(input_ids, attention_mask)
            input_shape = input_ids.size()
        elif inputs_embeds is not None:
            input_shape = inputs_embeds.size()[:-1]
        else:
            raise ValueError("You have to specify either input_ids or inputs_embeds")

        device = input_ids.device if input_ids is not None else inputs_embeds.device

        if attention_mask is None:
            attention_mask = torch.ones(input_shape, device=device)

        return self.span_predictor(
            input_ids,
            attention_mask,
            inputs_embeds=inputs_embeds,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
            return_dict=return_dict,
        )
