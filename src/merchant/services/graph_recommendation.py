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

"""Graph-based recommendation service using LightGCN product embeddings.

This service provides relationship-aware product recommendations by querying
the graph embedding collection in Milvus. It complements the semantic
retriever used by the ARAG recommendation agent.
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Any, TypedDict

from pymilvus import Collection, connections, utility

from src.merchant.config import get_settings
from src.merchant.services.agent_outcomes import record_agent_outcome

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================


class GraphRecommendationSettings:
    """Graph recommendation runtime settings."""

    def __init__(self) -> None:
        settings = get_settings()
        self.milvus_uri = settings.milvus_uri
        self.graph_collection_name = "product_catalog_graph"
        self.top_k = int(getattr(settings, "graph_recommendation_top_k", 10))
        self.min_similarity = float(
            getattr(settings, "graph_recommendation_min_similarity", 0.0)
        )
        self.timeout = float(getattr(settings, "graph_recommendation_timeout", 10.0))


# =============================================================================
# Input/Output Types
# =============================================================================


class GraphRecommendationInput(TypedDict):
    """Input for graph-based recommendation."""

    product_id: str
    exclude_ids: list[str]


class GraphRecommendationOutput(TypedDict):
    """Output from graph-based recommendation."""

    product_id: str
    product_name: str
    category: str
    score: float
    source: str


# =============================================================================
# Milvus Helpers
# =============================================================================


def _parse_milvus_uri(uri: str) -> tuple[str, str]:
    cleaned = uri.replace("http://", "").replace("https://", "")
    host, port = cleaned.split(":")
    return host, port


def _sanitize_milvus_string(value: str) -> str:
    """Escape single quotes for safe Milvus expression interpolation."""
    if not value:
        raise ValueError("product_id must not be empty")
    return value.replace("'", "''")


@contextmanager
def _get_graph_collection(settings: GraphRecommendationSettings):
    """Connect to Milvus and yield the graph collection."""
    host, port = _parse_milvus_uri(settings.milvus_uri)
    try:
        connections.connect(alias="graph_recsys", host=host, port=port)
    except Exception as exc:
        logger.warning("Failed to connect to Milvus for graph recommendations: %s", exc)
        yield None
        return

    try:
        if not utility.has_collection(settings.graph_collection_name):
            logger.warning(
                "Graph collection '%s' does not exist", settings.graph_collection_name
            )
            yield None
            return

        collection = Collection(settings.graph_collection_name)
        collection.load()
        yield collection
    finally:
        connections.disconnect(alias="graph_recsys")


def _search_graph_collection(
    collection: Collection,
    query_vector: list[float],
    top_k: int,
    exclude_ids: list[str],
) -> list[dict[str, Any]]:
    """Search graph collection and return ranked candidates."""
    search_params = {"metric_type": "L2", "params": {"nprobe": 5}}
    exclude_set = set(exclude_ids)

    results = collection.search(
        data=[query_vector],
        anns_field="graph_vector",
        param=search_params,
        limit=top_k + len(exclude_ids),
        output_fields=["id", "name", "category", "sku", "price_cents"],
    )

    hits = []
    for hit in results[0]:
        product_id = hit.entity.get("id")
        if not product_id or product_id in exclude_set:
            continue
        hits.append(
            {
                "product_id": product_id,
                "product_name": hit.entity.get("name", product_id),
                "category": hit.entity.get("category", ""),
                "score": float(hit.score),
                "sku": hit.entity.get("sku", ""),
                "price_cents": hit.entity.get("price_cents", 0),
            }
        )
        if len(hits) >= top_k:
            break

    return hits


# =============================================================================
# Core Service
# =============================================================================


async def get_graph_recommendations(
    product_id: str,
    exclude_ids: list[str] | None = None,
    top_k: int | None = None,
) -> list[GraphRecommendationOutput]:
    """Get graph-based recommendations for a product.

    Queries the Milvus graph embedding collection for products that are
    structurally related to the given product in the LightGCN graph.

    Args:
        product_id: Source product to find related items for.
        exclude_ids: Product IDs to exclude from results.
        top_k: Maximum number of recommendations to return.

    Returns:
        List of graph-based recommendations ordered by similarity.
    """
    started = time.perf_counter()
    status = "success"
    error_code: str | None = None
    settings = GraphRecommendationSettings()

    if exclude_ids is None:
        exclude_ids = []
    if top_k is None:
        top_k = settings.top_k

    try:
        with _get_graph_collection(settings) as collection:
            if collection is None:
                status = "fallback_success"
                error_code = "milvus_unavailable"
                return []

            expr = f"id == '{_sanitize_milvus_string(product_id)}'"
            rows = collection.query(expr=expr, output_fields=["graph_vector"])
            if not rows:
                status = "fallback_success"
                error_code = "product_not_found"
                return []

            query_vector = rows[0]["graph_vector"]
            hits = _search_graph_collection(
                collection, query_vector, top_k, exclude_ids + [product_id]
            )

            recommendations: list[GraphRecommendationOutput] = []
            for hit in hits:
                recommendations.append(
                    {
                        "product_id": hit["product_id"],
                        "product_name": hit["product_name"],
                        "category": hit["category"],
                        "score": hit["score"],
                        "source": "graph_lightgcn",
                    }
                )

            return recommendations
    except Exception as exc:
        status = "error_internal"
        error_code = "internal_exception"
        logger.warning(
            "Graph recommendation failed for product %s: %s", product_id, exc
        )
        return []
    finally:
        latency_ms = int((time.perf_counter() - started) * 1000)
        record_agent_outcome(
            agent_type="graph_recommendation",
            channel="acp",
            status=status,
            latency_ms=latency_ms,
            session_id=None,
            error_code=error_code,
        )


async def get_graph_recommendations_for_cart(
    cart_product_ids: list[str],
    exclude_ids: list[str] | None = None,
    top_k: int | None = None,
) -> list[GraphRecommendationOutput]:
    """Get graph-based recommendations for a cart of products.

    Queries graph embeddings for each cart product and merges the results,
    deduplicating by product_id and keeping the best scores.

    Args:
        cart_product_ids: List of product IDs in the cart.
        exclude_ids: Additional product IDs to exclude.
        top_k: Maximum number of recommendations to return.

    Returns:
        Merged list of graph-based recommendations ordered by score.
    """
    if exclude_ids is None:
        exclude_ids = []
    if top_k is None:
        top_k = 10

    seen: dict[str, GraphRecommendationOutput] = {}
    for product_id in cart_product_ids:
        recommendations = await get_graph_recommendations(
            product_id=product_id,
            exclude_ids=exclude_ids + list(seen.keys()),
            top_k=top_k,
        )
        for rec in recommendations:
            pid = rec["product_id"]
            if pid not in seen or rec["score"] < seen[pid]["score"]:
                seen[pid] = rec

    merged = sorted(seen.values(), key=lambda item: item["score"])
    return merged[:top_k]


def get_graph_embeddings_for_products(
    product_ids: list[str],
) -> list[dict[str, Any]]:
    """Retrieve stored graph embeddings for the given products.

    This is a synchronous helper used by tests and offline scripts to
    inspect graph embeddings without running the full Milvus stack.

    Args:
        product_ids: List of product IDs to look up.

    Returns:
        List of dicts with product_id and embedding vector.
    """
    from src.data.product_catalog import PRODUCTS
    from src.data.product_graph import LightGCNConfig, train_lightgcn

    by_id = {p["id"]: p for p in PRODUCTS}
    products = [by_id[pid] for pid in product_ids if pid in by_id]
    if not products:
        return []

    config = LightGCNConfig(
        embedding_dim=32, num_layers=2, epochs=20, negative_samples=2
    )
    result = train_lightgcn(products, config)
    return [
        {"product_id": pid, "embedding": emb}
        for pid, emb in zip(product_ids, result.embeddings, strict=True)
    ]
