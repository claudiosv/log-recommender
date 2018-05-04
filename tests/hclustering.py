from deepdiff import DeepDiff
from log_recommender.hclustering import ClusteringTree, tree_from_dendrogram, break_into_multiple_trees_by_wfs

__author__ = 'hlib'

import unittest

class HClusteringTest(unittest.TestCase):
    def test_tree_from_dendrogram_trivial(self):

        dendrogram = [[0, 1]]

        expected = ClusteringTree.node(2, ClusteringTree.leaf(0), ClusteringTree.leaf(1))

        actual = tree_from_dendrogram(dendrogram)

        self.assertEqual(DeepDiff(expected, actual), {})

    def test_tree_from_dendrogram_simple(self):

        dendrogram = [[0, 1],[3, 2]]

        expected = ClusteringTree.node(4,
            ClusteringTree.node(3, ClusteringTree.leaf(0), ClusteringTree.leaf(1)),
            ClusteringTree.leaf(2)
        )

        actual = tree_from_dendrogram(dendrogram)

    def test_tree_from_dendrogram_medium(self):

        dendrogram = [[3, 4], [6, 5], [1, 2], [8, 7], [0, 9]]

        expected = ClusteringTree.node(10,
                                       ClusteringTree.leaf(0),
                                       ClusteringTree.node(9,
                                                           ClusteringTree.node(8, ClusteringTree.leaf(1), ClusteringTree.leaf(2)),
                                                           ClusteringTree.node(7,
                                                                               ClusteringTree.node(6,
                                                                                                   ClusteringTree.leaf(3),
                                                                                                   ClusteringTree.leaf(4)),
                                                                               ClusteringTree.leaf(5))))

        actual = tree_from_dendrogram(dendrogram)

        self.assertEqual(DeepDiff(expected, actual), {})

        self.assertEqual(DeepDiff(expected, actual), {})

    def test_break_into_multiple_trees_by_wfs_trivial(self):
        tree = ClusteringTree.node(10,
                                       ClusteringTree.leaf(0),
                                       ClusteringTree.node(9,
                                                           ClusteringTree.node(8, ClusteringTree.leaf(1), ClusteringTree.leaf(2)),
                                                           ClusteringTree.node(7,
                                                                               ClusteringTree.node(6,
                                                                                                   ClusteringTree.leaf(3),
                                                                                                   ClusteringTree.leaf(4)),
                                                                               ClusteringTree.leaf(5))))
        expected = [tree]

        actual = break_into_multiple_trees_by_wfs(tree, 1)

        self.assertEqual(DeepDiff(expected, actual), {})

    def test_break_into_multiple_trees_by_wfs_simple(self):
        tree = ClusteringTree.node(10,
                                       ClusteringTree.leaf(0),
                                       ClusteringTree.node(9,
                                                           ClusteringTree.node(8, ClusteringTree.leaf(1), ClusteringTree.leaf(2)),
                                                           ClusteringTree.node(7,
                                                                               ClusteringTree.node(6,
                                                                                                   ClusteringTree.leaf(3),
                                                                                                   ClusteringTree.leaf(4)),
                                                                               ClusteringTree.leaf(5))))

        expected = [ClusteringTree.leaf(0), ClusteringTree.node(9,
                                                           ClusteringTree.node(8, ClusteringTree.leaf(1), ClusteringTree.leaf(2)),
                                                           ClusteringTree.node(7,
                                                                               ClusteringTree.node(6,
                                                                                                   ClusteringTree.leaf(3),
                                                                                                   ClusteringTree.leaf(4)),
                                                                               ClusteringTree.leaf(5)))]

        actual = break_into_multiple_trees_by_wfs(tree, 2)

        self.assertEqual(DeepDiff(expected, actual), {})

    def test_break_into_multiple_trees_by_wfs_equal(self):
        tree = ClusteringTree.node(14,
                                       ClusteringTree.node(12,
                                                            ClusteringTree.node(8,
                                                                               ClusteringTree.leaf(0),
                                                                               ClusteringTree.leaf(1)),
                                                            ClusteringTree.node(9,
                                                                               ClusteringTree.leaf(2),
                                                                               ClusteringTree.leaf(3))),

                                       ClusteringTree.node(13,
                                                            ClusteringTree.node(10,
                                                                               ClusteringTree.leaf(4),
                                                                               ClusteringTree.leaf(5)),
                                                            ClusteringTree.node(11,
                                                                               ClusteringTree.leaf(6),
                                                                               ClusteringTree.leaf(7))))

        expected = [ClusteringTree.node(8, ClusteringTree.leaf(0), ClusteringTree.leaf(1)),
                    ClusteringTree.node(9, ClusteringTree.leaf(2), ClusteringTree.leaf(3)),
                    ClusteringTree.node(10, ClusteringTree.leaf(4), ClusteringTree.leaf(5)),
                    ClusteringTree.node(11, ClusteringTree.leaf(6), ClusteringTree.leaf(7))]

        actual = break_into_multiple_trees_by_wfs(tree, 4)

        self.assertEqual(DeepDiff(expected, actual), {})

    def test_get_all_leaf_payloads(self):
        tree = ClusteringTree.node(10,
                               ClusteringTree.leaf(0),
                               ClusteringTree.node(9,
                                                   ClusteringTree.node(8, ClusteringTree.leaf(1), ClusteringTree.leaf(2)),
                                                   ClusteringTree.node(7,
                                                                       ClusteringTree.node(6,
                                                                                           ClusteringTree.leaf(3),
                                                                                           ClusteringTree.leaf(4)),
                                                                       ClusteringTree.leaf(5))))
        expected = [0, 1, 2, 3, 4, 5]

        actual = tree.get_all_leaf_payloads()

        self.assertEqual(DeepDiff(expected, actual), {})



if __name__ == '__main__':
    unittest.main()