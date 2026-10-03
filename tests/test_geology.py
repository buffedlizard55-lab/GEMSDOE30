import unittest
import numpy as np
from gemsdoe30.geology import interaction_features

class GeologyTests(unittest.TestCase):
    def test_constant_fields_have_no_edges(self):
        a=np.ones((3,30,30),dtype=np.float32)
        h,c=interaction_features(a,['geod_dilaterate','cond_surf','depth_to_base_surf'])
        self.assertTrue(np.all(h[:,6:-6,6:-6]==0))
        self.assertTrue(np.all(c[:,6:-6,6:-6]==0))
    def test_missing_names_fail(self):
        with self.assertRaises(ValueError):
            interaction_features(np.ones((3,30,30)),['a','b','c'])
