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

"""Tests for the graph recommendation service."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.merchant.services.graph_recommendation import (
    GraphRecommendationOutput,
    _search_graph_collection,
    get_graph_recommendations,
    get_graph_recommendations_for_cart,
    get_graph_embeddings_for_products,
)


class TestGraphRecommendations:
    """Tests for graph-based recommendation functions."""

    def test_get_graph_embeddings_for_products_known_ids(self) -> None:
        """Returns embeddings for known product IDs."""
        results = get_graph_embeddings_for_products(["prod_1", "prod_5"])
        assert len(results) == 2
        assert results[0]["product_id"] == "prod_1"
        assert len(results[0]["embedding"]) > 0

    def test_get_graph_embeddings_for_products_unknown_ids(self) -> None:
        """Returns empty list for unknown product IDs."""
        results = get_graph_embeddings_for_products(["prod_999"])
        assert results == []

    @patch("src.merchant.services.graph_recommendation._get_graph_collection")
    def test_get_graph_recommendations_success(self, mock_get_collection: MagicMock) -> None:
        """Returns recommendations when Milvus is available."""
        mock_collection = MagicMock()
        entity_mock = MagicMock()
        entity_mock.get.side_effect = lambda k, d=None: {
            "id": "prod_5",
            "name": "Classic Denim Jeans",
            "category": "bottoms",
        }.get(k, d)
        hit = MagicMock()
        hit.entity = entity_mock
        hit.score = 0.05
        mock_collection.query.return_value = [{"graph_vector": [0.1] * 64}]
        mock_collection.search.return_value = [[hit]]
        mock_get_collection.return_value = mock_collection

        results = asyncio.get_event_loop().run_until_complete(
            get_graph_recommendations("prod_1", top_k=1)
        )
        assert len(results) == 1
        assert results[0]["product_id"] == "prod_5"
        assert results[0]["source"] == "graph_lightgcn"

    @patch("src.merchant.services.graph_recommendation._get_graph_collection")
    def test_get_graph_recommendations_milvus_unavailable(self, mock_get_collection: MagicMock) -> None:
        """Returns empty list when Milvus is unavailable."""
        mock_get_collection.return_value = None
        results = asyncio.get_event_loop().run_until_complete(
            get_graph_recommendations("prod_1")
        )
        assert results == []

    @patch("src.merchant.services.graph_recommendation.get_graph_recommendations")
    def test_get_graph_recommendations_for_cart_merges_results(self, mock_rec: AsyncMock) -> None:
        """Merges and deduplicates recommendations across cart items."""
        mock_rec.return_value = [
            {
                "product_id": "prod_5",
                "product_name": "Classic Denim Jeans",
                "category": "bottoms",
                "score": 0.05,
                "source": "graph_lightgcn",
            }
        ]

        results = asyncio.get_event_loop().run_until_complete(
            get_graph_recommendations_for_cart(["prod_1", "prod_9"], top_k=2)
        )
        assert len(results) == 1
        assert results[0]["product_id"] == "prod_5"
