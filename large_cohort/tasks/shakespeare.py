# Copyright 2019, Google LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Configures federated Shakespeare character prediction tasks."""

import functools

import tensorflow as tf
import tensorflow_federated as tff

from large_cohort import simulation_specs
from utils import keras_metrics
from utils.datasets import shakespeare_dataset
from utils.models import shakespeare_models

SEQUENCE_LENGTH = 80
# Vocabulary with OOV ID, zero for the padding, and BOS, EOS IDs.
VOCAB_SIZE = len(shakespeare_dataset.CHAR_VOCAB) + 4


def _metrics_builder():
  """Returns a `list` of `tf.keras.metric.Metric` objects."""
  pad_token, _, _, _ = shakespeare_dataset.get_special_tokens()

  return [
      keras_metrics.NumBatchesCounter(),
      keras_metrics.NumExamplesCounter(),
      keras_metrics.NumTokensCounter(masked_tokens=[pad_token]),
      keras_metrics.MaskedCategoricalAccuracy(masked_tokens=[pad_token]),
  ]


def get_model_spec(seed: int = 0) -> simulation_specs.ModelSpec:
  """Configures a model for Shakespeare tasks."""
  keras_model_builder = functools.partial(
      shakespeare_models.create_recurrent_model,
      vocab_size=VOCAB_SIZE,
      sequence_length=SEQUENCE_LENGTH,
      seed=seed)
  loss_builder = functools.partial(
      tf.keras.losses.SparseCategoricalCrossentropy, from_logits=True)
  return simulation_specs.ModelSpec(
      keras_model_builder=keras_model_builder,
      loss_builder=loss_builder,
      metrics_builder=_metrics_builder)


def get_data_spec(
    train_client_spec: simulation_specs.ClientSpec,
    eval_client_spec: simulation_specs.ClientSpec,
    use_synthetic_data: bool = False) -> simulation_specs.DataSpec:
  """Configures data for Shakespeare next character prediction.

  Args:
    train_client_spec: A `simulation_specs.ClientSpec` used to configure
      training clients.
    eval_client_spec: A `simulation_specs.ClientSpec` used to configure
      evaluation clients.
    use_synthetic_data: A boolean indicating whether to use synthetic data.
      Suitable for testing purposes.

  Returns:
    A `simulation_specs.DataSpec`.
  """
  if use_synthetic_data:
    synthetic_data = tff.simulation.datasets.shakespeare.get_synthetic()
    train_data = synthetic_data
    validation_data = synthetic_data
    test_data = synthetic_data
  else:
    train_data, test_data = tff.simulation.datasets.shakespeare.load_data()
    validation_data = None

  train_preprocess_fn = shakespeare_dataset.create_preprocess_fn(
      num_epochs=train_client_spec.num_epochs,
      batch_size=train_client_spec.batch_size,
      sequence_length=SEQUENCE_LENGTH)

  eval_preprocess_fn = shakespeare_dataset.create_preprocess_fn(
      num_epochs=eval_client_spec.num_epochs,
      batch_size=eval_client_spec.batch_size,
      shuffle_buffer_size=1,
      sequence_length=SEQUENCE_LENGTH)

  return simulation_specs.DataSpec(
      train_data=train_data,
      validation_data=validation_data,
      test_data=test_data,
      train_preprocess_fn=train_preprocess_fn,
      eval_preprocess_fn=eval_preprocess_fn)
