# coding=utf-8
# Copyright 2010, FLMR authors, The Hugging Face Team.
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
""" FLMR model configuration"""

from ...configuration_utils import PretrainedConfig
from ...utils import logging


logger = logging.get_logger(__name__)

FLMR_PRETRAINED_CONFIG_ARCHIVE_MAP = {
    "weizhelin/flmr": "https://huggingface.co/weizhelin/flmr/resolve/main/config.json",
}



class FLMRConfig(PretrainedConfig):
    r"""
    [`FLMRConfig`] is the configuration class to store the configuration of a *FLMRModel*.

    This is the configuration class to store the configuration of a [`FLMRContextEncoder`], [`FLMRQuestionEncoder`], or a
    [`FLMRReader`]. It is used to instantiate the components of the FLMR model according to the specified arguments,
    defining the model component architectures. Instantiating a configuration with the defaults will yield a similar
    configuration to that of the FLMRContextEncoder
    [weizhelin/flmr](https://huggingface.co/weizhelin/flmr)
    architecture.

    This class is a subclass of [`BertConfig`]. Please check the superclass for the documentation of all kwargs.

    Args:
        vocab_size (`int`, *optional*, defaults to 30522):
            Vocabulary size of the FLMR model. Defines the different tokens that can be represented by the *inputs_ids*
            passed to the forward method of [`BertModel`].
        hidden_size (`int`, *optional*, defaults to 768):
            Dimensionality of the encoder layers and the pooler layer.
        num_hidden_layers (`int`, *optional*, defaults to 12):
            Number of hidden layers in the Transformer encoder.
        num_attention_heads (`int`, *optional*, defaults to 12):
            Number of attention heads for each attention layer in the Transformer encoder.
        intermediate_size (`int`, *optional*, defaults to 3072):
            Dimensionality of the "intermediate" (i.e., feed-forward) layer in the Transformer encoder.
        hidden_act (`str` or `function`, *optional*, defaults to `"gelu"`):
            The non-linear activation function (function or string) in the encoder and pooler. If string, `"gelu"`,
            `"relu"`, `"silu"` and `"gelu_new"` are supported.
        hidden_dropout_prob (`float`, *optional*, defaults to 0.1):
            The dropout probability for all fully connected layers in the embeddings, encoder, and pooler.
        attention_probs_dropout_prob (`float`, *optional*, defaults to 0.1):
            The dropout ratio for the attention probabilities.
        max_position_embeddings (`int`, *optional*, defaults to 512):
            The maximum sequence length that this model might ever be used with. Typically set this to something large
            just in case (e.g., 512 or 1024 or 2048).
        type_vocab_size (`int`, *optional*, defaults to 2):
            The vocabulary size of the *token_type_ids* passed into [`BertModel`].
        initializer_range (`float`, *optional*, defaults to 0.02):
            The standard deviation of the truncated_normal_initializer for initializing all weight matrices.
        layer_norm_eps (`float`, *optional*, defaults to 1e-12):
            The epsilon used by the layer normalization layers.
        pad_token_id (`int`, *optional*, defaults to 0):
            Padding token id.
        position_embedding_type (`str`, *optional*, defaults to `"absolute"`):
            Type of position embedding. Choose one of `"absolute"`, `"relative_key"`, `"relative_key_query"`. For
            positional embeddings use `"absolute"`. For more information on `"relative_key"`, please refer to
            [Self-Attention with Relative Position Representations (Shaw et al.)](https://arxiv.org/abs/1803.02155).
            For more information on `"relative_key_query"`, please refer to *Method 4* in [Improve Transformer Models
            with Better Relative Position Embeddings (Huang et al.)](https://arxiv.org/abs/2009.13658).
        projection_dim (`int`, *optional*, defaults to 0):
            Dimension of the projection for the context and question encoders. If it is set to zero (default), then no
            projection is done.

    Example:

    ```python
    >>> from transformers import FLMRConfig, FLMRContextEncoder

    >>> # Initializing a FLMR weizhelin/flmr style configuration
    >>> configuration = FLMRConfig()

    >>> # Initializing a model (with random weights) from the weizhelin/flmr style configuration
    >>> model = FLMRContextEncoder(configuration)

    >>> # Accessing the model configuration
    >>> configuration = model.config
    ```"""

    model_type = "flmr"

    def __init__(
        self,
        vocab_size=30522,
        hidden_size=768,
        dim=128,
        num_hidden_layers=12,
        num_attention_heads=12,
        intermediate_size=3072,
        hidden_act="gelu",
        hidden_dropout_prob=0.1,
        attention_probs_dropout_prob=0.1,
        max_position_embeddings=512,
        type_vocab_size=2,
        initializer_range=0.02,
        layer_norm_eps=1e-12,
        pad_token_id=0,
        position_embedding_type="absolute",
        projection_dim: int = 0,
        mask_punctuation: bool = True,
        mapping_network_prefix_length: int = 32,
        vision_encoder_dim: int = 768,
        use_vision_encoder: bool = True,
        # vision_model_config_class: str = "CLIPVisionConfig",
        # vision_model_class: str = "CLIPVisionModel",
        vision_model_version: str = "openai/clip-vit-base-patch32",
        separate_query_and_context_text_encoder: bool = False,
        separate_query_and_context_vision_encoder: bool = False,
        query_concat_output_from_vision_encoder: bool = True,
        query_concat_output_from_text_encoder: bool = True,
        context_concat_output_from_vision_encoder: bool = False,
        context_concat_output_from_text_encoder: bool = True,
        **kwargs,
    ):
        super().__init__(pad_token_id=pad_token_id, **kwargs)

        self.vocab_size = vocab_size
        self.hidden_size = hidden_size
        self.dim = dim
        self.num_hidden_layers = num_hidden_layers
        self.num_attention_heads = num_attention_heads
        self.hidden_act = hidden_act
        self.intermediate_size = intermediate_size
        self.hidden_dropout_prob = hidden_dropout_prob
        self.attention_probs_dropout_prob = attention_probs_dropout_prob
        self.max_position_embeddings = max_position_embeddings
        self.type_vocab_size = type_vocab_size
        self.initializer_range = initializer_range
        self.layer_norm_eps = layer_norm_eps
        self.projection_dim = projection_dim
        self.position_embedding_type = position_embedding_type
        self.mask_punctuation = mask_punctuation
        self.mapping_network_prefix_length = mapping_network_prefix_length
        self.vision_encoder_dim = vision_encoder_dim
        # self.vision_model_config_class = vision_model_config_class
        # self.vision_model_class = vision_model_class
        self.vision_model_version = vision_model_version
        self.use_vision_encoder = use_vision_encoder
        self.separate_query_and_context_text_encoder = separate_query_and_context_text_encoder
        self.separate_query_and_context_vision_encoder = separate_query_and_context_vision_encoder
        self.query_concat_output_from_vision_encoder = query_concat_output_from_vision_encoder
        self.query_concat_output_from_text_encoder = query_concat_output_from_text_encoder
        self.context_concat_output_from_vision_encoder = context_concat_output_from_vision_encoder
        self.context_concat_output_from_text_encoder = context_concat_output_from_text_encoder

