# app/models/duplicate_detector.py

from typing import Dict, List, Tuple

from ..utils.embeddings import TitleEmbedder


class SemanticDuplicateDetector:
    """
    Detects near-duplicate product listings using TF-IDF cosine similarity.

    Two listings are considered duplicates when their title similarity exceeds
    ``similarity_threshold``.  Cross-platform duplicates (same item listed on
    both Google Shopping and eBay) are flagged separately — they are informative
    rather than suspicious.

    Usage
    -----
    >>> detector = SemanticDuplicateDetector()
    >>> products = detector.flag_duplicates(products)
    >>> summary = detector.duplicate_summary(products)
    """

    def __init__(self, similarity_threshold: float = 0.82):
        self.similarity_threshold = similarity_threshold
        self._embedder = TitleEmbedder(ngram_range=(1, 2), max_features=10_000)

    # ── Public API ────────────────────────────────────────────────────

    def flag_duplicates(self, products: List[Dict]) -> List[Dict]:
        """
        Add duplicate metadata to each product in-place and return the list.

        Fields added to each product:
            ``duplicate_group``     : int | None  — shared ID for all members of a group
            ``is_cross_platform``   : bool        — True if duplicates span platforms
            ``similar_to``          : List[Dict]  — brief info on matched products
        """
        if len(products) < 2:
            return products

        titles = [p.get("title", "") for p in products]
        sim_matrix = self._embedder.similarity_matrix(titles)

        # Build adjacency: pairs above threshold (excluding diagonal)
        pairs: List[Tuple[int, int, float]] = []
        n = len(products)
        for i in range(n):
            for j in range(i + 1, n):
                score = float(sim_matrix[i, j])
                if score >= self.similarity_threshold:
                    pairs.append((i, j, score))

        # Union-Find to cluster duplicates into groups
        parent = list(range(n))

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x: int, y: int) -> None:
            parent[find(x)] = find(y)

        for i, j, _ in pairs:
            union(i, j)

        # Map root → group_id (only for products with at least one duplicate)
        roots_with_duplicates = {find(i) for i, j, _ in pairs} | {find(j) for i, j, _ in pairs}
        root_to_group = {r: gid for gid, r in enumerate(sorted(roots_with_duplicates), start=1)}

        # Initialise metadata on all products
        for p in products:
            p.setdefault("duplicate_group", None)
            p.setdefault("is_cross_platform", False)
            p.setdefault("similar_to", [])

        # Populate per-product metadata
        for i, j, score in pairs:
            gi, gj = find(i), find(j)
            group_id = root_to_group.get(gi) or root_to_group.get(gj)

            for src, tgt in [(i, j), (j, i)]:
                products[src]["duplicate_group"] = group_id
                products[src]["similar_to"].append({
                    "title":      products[tgt].get("title", ""),
                    "price":      products[tgt].get("price"),
                    "platform":   products[tgt].get("platform", ""),
                    "similarity": round(score, 3),
                })

            # Cross-platform flag
            p_platform = products[i].get("platform", "").lower()
            q_platform = products[j].get("platform", "").lower()
            if p_platform != q_platform:
                products[i]["is_cross_platform"] = True
                products[j]["is_cross_platform"] = True

        return products

    def duplicate_summary(self, products: List[Dict]) -> Dict:
        """
        Aggregate duplicate statistics for inclusion in the API response.

        Returns
        -------
        {
            "total_duplicates": int,          # products in any duplicate group
            "duplicate_groups": int,          # number of distinct clusters
            "cross_platform_pairs": int,      # listings that match across platforms
            "groups": [                       # one entry per cluster
                {
                    "group_id": int,
                    "count": int,
                    "titles": [str, ...],
                    "platforms": [str, ...],
                    "cross_platform": bool,
                }
            ]
        }
        """
        in_group = [p for p in products if p.get("duplicate_group") is not None]
        cross_platform = [p for p in in_group if p.get("is_cross_platform")]

        # Cluster by group_id
        groups: Dict[int, List[Dict]] = {}
        for p in in_group:
            gid = p["duplicate_group"]
            groups.setdefault(gid, []).append(p)

        group_summaries = []
        for gid, members in sorted(groups.items()):
            platforms = list({m.get("platform", "unknown") for m in members})
            group_summaries.append({
                "group_id":       gid,
                "count":          len(members),
                "titles":         [m.get("title", "") for m in members],
                "prices":         [m.get("price") for m in members],
                "platforms":      platforms,
                "cross_platform": len(platforms) > 1,
            })

        return {
            "total_duplicates":    len(in_group),
            "duplicate_groups":    len(groups),
            "cross_platform_pairs": len(cross_platform),
            "groups":              group_summaries,
        }
