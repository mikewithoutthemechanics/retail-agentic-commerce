# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Lightweight LightGCN implementation for product graph embeddings.

This module provides a pure Python implementation of LightGCN suitable for
small product graphs. It avoids heavyweight deep-learning dependencies while
still generating relationship-aware embeddings for downstream Milvus indexing.
"""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass

from src.data.product_catalog import ProductData, build_product_graph_edges

logger = logging.getLogger(__name__)


@dataclass
class LightGCNConfig:
    """Hyperparameters for LightGCN training."""

    embedding_dim: int = 64
    num_layers: int = 3
    learning_rate: float = 0.01
    epochs: int = 200
    negative_samples: int = 5
    seed: int = 42


@dataclass
class LightGCNResult:
    """Outputs from LightGCN training."""

    embeddings: list[list[float]]
    id_to_index: dict[str, int]
    index_to_id: dict[int, str]
    loss_history: list[float]


def _build_adjacency(
    products: list[ProductData],
    category_edges: list[tuple[str, str]],
    co_purchase_edges: list[tuple[str, str]],
    style_edges: list[tuple[str, str, float]],
) -> list[list[float]]:
    """Build symmetric adjacency matrix with weighted edges."""
    n = len(products)
    adj = [[0.0] * n for _ in range(n)]

    def add_edge(u: str, v: str, weight: float = 1.0) -> None:
        iu = _id_index(products, u)
        iv = _id_index(products, v)
        adj[iu][iv] = max(adj[iu][iv], weight)
        adj[iv][iu] = max(adj[iv][iu], weight)

    for u, v in category_edges:
        add_edge(u, v, 1.0)

    for u, v in co_purchase_edges:
        add_edge(u, v, 1.5)

    for u, v, score in style_edges:
        add_edge(u, v, float(score))

    return adj


def _id_index(products: list[ProductData], product_id: str) -> int:
    for idx, product in enumerate(products):
        if product["id"] == product_id:
            return idx
    raise ValueError(f"Unknown product id: {product_id}")


def _normalized_adjacency(adj: list[list[float]]) -> list[list[float]]:
    """Compute symmetrically normalized adjacency matrix used by LightGCN."""
    n = len(adj)
    norm = [[0.0] * n for _ in range(n)]
    degrees = [sum(adj[i][j] for j in range(n)) for i in range(n)]
    for i in range(n):
        if degrees[i] <= 0:
            continue
        for j in range(n):
            if degrees[j] <= 0:
                continue
            norm[i][j] = adj[i][j] / math.sqrt(degrees[i] * degrees[j])
    return norm


def _matmul(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    n = len(a)
    m = len(b[0]) if b else 0
    k = len(b)
    result = [[0.0] * m for _ in range(n)]
    for i in range(n):
        for j in range(m):
            s = 0.0
            for p in range(k):
                s += a[i][p] * b[p][j]
            result[i][j] = s
    return result


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def _bpr_loss_and_gradients(
    embeddings: list[list[float]],
    pairs: list[tuple[int, int]],
    negative_pairs: list[list[int]],
    num_nodes: int,
    dim: int,
) -> tuple[float, list[list[float]]]:
    grads = [[0.0] * dim for _ in range(num_nodes)]
    total_loss = 0.0
    count = 0

    for (u, v), neg_group in zip(pairs, negative_pairs):
        user_vec = embeddings[u]
        pos_vec = embeddings[v]
        pos_logit = _dot(user_vec, pos_vec)

        for neg in neg_group:
            neg_vec = embeddings[neg]
            neg_logit = _dot(user_vec, neg_vec)
            diff = pos_logit - neg_logit
            sig = _sigmoid(diff)
            total_loss += -math.log(max(1.0 - sig, 1e-9))

            for d in range(dim):
                pu = (1.0 - sig) * pos_vec[d]
                pv = (1.0 - sig) * user_vec[d]
                nu = -sig * neg_vec[d]
                nv = -sig * user_vec[d]
                grads[u][d] += pu + nu
                grads[v][d] += pv
                grads[neg][d] += nv
            count += 1

    if count == 0:
        return 0.0, grads
    return total_loss / count, grads


def train_lightgcn(
    products: list[ProductData],
    config: LightGCNConfig | None = None,
) -> LightGCNResult:
    """Train LightGCN on the product graph and return node embeddings."""
    if config is None:
        config = LightGCNConfig()

    if len(products) < 2:
        raise ValueError("LightGCN requires at least 2 products")

    random.seed(config.seed)

    category_edges, co_purchase_edges, style_edges = build_product_graph_edges(products)
    adj = _build_adjacency(products, category_edges, co_purchase_edges, style_edges)
    norm_adj = _normalized_adjacency(adj)

    id_to_index = {product["id"]: idx for idx, product in enumerate(products)}
    index_to_id = {idx: product["id"] for idx, product in enumerate(products)}

    n = len(products)
    dim = config.embedding_dim
    embeddings = [[random.gauss(0, 0.01) for _ in range(dim)] for _ in range(n)]

    positive_pairs = [(i, j) for i in range(n) for j in range(n) if adj[i][j] > 0]
    if not positive_pairs:
        raise ValueError("Product graph has no edges; cannot train LightGCN")

    loss_history: list[float] = []

    for epoch in range(config.epochs):
        sampled = [random.choice(positive_pairs) for _ in range(min(512, len(positive_pairs)))]
        neg = [[random.randint(0, n - 1) for _ in range(config.negative_samples)] for _ in sampled]

        loss, grads = _bpr_loss_and_gradients(embeddings, sampled, neg, n, dim)

        scale = config.learning_rate / (len(sampled) * (1 + config.negative_samples))
        for i in range(n):
            norm = math.sqrt(sum(g * g for g in grads[i])) + 1e-9
            for d in range(dim):
                embeddings[i][d] -= scale * grads[i][d] / norm
            emb_norm = math.sqrt(sum(e * e for e in embeddings[i])) + 1e-9
            for d in range(dim):
                embeddings[i][d] /= emb_norm

        loss_history.append(loss)
        if epoch % 20 == 0:
            logger.info("LightGCN epoch=%d loss=%.4f", epoch, loss)

    layer_embeddings = [embeddings]
    current = embeddings
    for _ in range(config.num_layers - 1):
        current = _matmul(norm_adj, current)
        layer_embeddings.append(current)

    final_embeddings = [
        [layer[i][d] for layer in layer_embeddings for d in range(dim)]
        for i in range(n)
    ]

    return LightGCNResult(
        embeddings=final_embeddings,
        id_to_index=id_to_index,
        index_to_id=index_to_id,
        loss_history=loss_history,
    )


def get_graph_embeddings(
    products: list[ProductData],
    config: LightGCNConfig | None = None,
) -> list[list[float]]:
    """Return graph embeddings ordered by product id."""
    result = train_lightgcn(products, config)
    return result.embeddings
