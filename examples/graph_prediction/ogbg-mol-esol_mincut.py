"""
This example shows how to perform molecule regression with the
[Open Graph Benchmark](https://ogb.stanford.edu) `mol-esol` dataset, using a
simple GCN with MinCutPool in batch mode.
Expect unstable training due to the small-ish size of the dataset.
"""

import numpy as np
from ogb.graphproppred import GraphPropPredDataset, Evaluator
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.layers import Input, Dense
from tensorflow.keras.models import Model
from tensorflow.keras.optimizers import Adam

from spektral.data import BatchLoader
from spektral.datasets import OGB
from spektral.layers import GCNConv, MinCutPool, GlobalSumPool

################################################################################
# PARAMETERS
################################################################################
learning_rate = 1e-3  # Learning rate
epochs = 10           # Number of training epochs
batch_size = 32       # Batch size

################################################################################
# LOAD DATA
################################################################################
dataset_name = 'ogbg-molesol'
ogb_dataset = GraphPropPredDataset(name=dataset_name)
dataset = OGB(ogb_dataset)

# Parameters
N = max(g.n_nodes for g in dataset)
F = dataset.n_node_features  # Dimension of node features
S = dataset.n_edge_features  # Dimension of edge features
n_out = dataset.n_labels     # Dimension of the target

# Train/test split
idx = ogb_dataset.get_idx_split()
idx_tr, idx_va, idx_te = idx["train"], idx["valid"], idx["test"]
dataset_tr = dataset[idx_tr]
dataset_va = dataset[idx_va]
dataset_te = dataset[idx_te]

################################################################################
# BUILD MODEL
################################################################################
X_in = Input(shape=(None, F))
A_in = Input(shape=(None, None))

X_1 = GCNConv(32, activation='relu')([X_in, A_in])
X_1, A_1 = MinCutPool(N // 2)([X_1, A_in])
X_2 = GCNConv(32, activation='relu')([X_1, A_1])
X_3 = GlobalSumPool()(X_2)
output = Dense(n_out)(X_3)

# Build model
model = Model(inputs=[X_in, A_in], outputs=output)
opt = Adam(lr=learning_rate)
model.compile(optimizer=opt, loss='mse')
model.summary()

################################################################################
# FIT MODEL
################################################################################
loader_tr = BatchLoader(dataset_tr, batch_size=batch_size)
loader_va = BatchLoader(dataset_va, batch_size=batch_size)
model.fit(loader_tr,
          steps_per_epoch=loader_tr.steps_per_epoch,
          epochs=epochs,
          validation_data=loader_va,
          validation_steps=loader_va.steps_per_epoch,
          callbacks=[EarlyStopping(patience=10, restore_best_weights=True)])

################################################################################
# EVALUATE MODEL
################################################################################
print('Testing model')
evaluator = Evaluator(name=dataset_name)
loader_te = BatchLoader(dataset_te, batch_size=batch_size, epochs=1)
y_pred = model.predict(loader_te, batch_size=batch_size)
y_true = np.vstack([g.y for g in dataset_te])
ogb_score = evaluator.eval({'y_true': y_true, 'y_pred': y_pred})
print('Done. RMSE: {:.4f}'.format(ogb_score['rmse']))
