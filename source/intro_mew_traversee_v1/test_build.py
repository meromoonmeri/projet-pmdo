"""Tests dédiés — IMW3 « Traversée » (nouvelle intro dans l'esprit Treasure Town). Lancer : .venv/bin/python -m unittest source.intro_mew_traversee_v1.test_build -v (après build.py)."""
import importlib.util, json, unittest
from pathlib import Path
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
O = R / 'renders/intro_mew_traversee_v1'
spec = importlib.util.spec_from_file_location('imw3_build', HERE / 'build.py')
B = importlib.util.module_from_spec(spec); spec.loader.exec_module(B)
M = json.loads((O / 'manifest.json').read_text())


class Traversee(unittest.TestCase):
    def test_format_et_actes(self):
        self.assertEqual(M['format']['size_px'], [B.W, B.H])
        self.assertEqual(M['format']['fps'], B.FPS)
        self.assertEqual(M['format']['frames'], B.N_FRAMES)
        self.assertAlmostEqual(M['format']['duree_s'], B.T_END, places=3)
        self.assertEqual(M['format']['frames'], int(round(B.T_END * B.FPS)))
        actes = M['actes']
        self.assertEqual(len(actes), 3)
        for a, b in zip(actes, actes[1:]):
            self.assertAlmostEqual(a['t_fin_s'], b['t_debut_s'])
            self.assertLess(a['t_debut_s'], a['t_fin_s'])
        self.assertAlmostEqual(actes[0]['t_debut_s'], 0.0)
        self.assertAlmostEqual(actes[-1]['t_fin_s'], B.T_END)

    def test_cadres_deterministes(self):
        for t in (0.2, 3.5, 7.8, 12.0, 18.0, 23.0, 26.5):
            a = B.render(t)
            self.assertEqual(a.shape, (B.H, B.W, 3))
            self.assertEqual(a.dtype, np.uint8)
            self.assertTrue((a == B.render(t)).all(), f'non déterministe à t={t}')
        self.assertFalse((B.render(3.0) == B.render(3.2)).all(), 'l image doit bouger')

    def test_pas_de_magenta_ni_de_noir_plat(self):
        for t in np.linspace(1.0, B.T_END - 1.2, 18):
            a = B.render(float(t)).astype(int)
            self.assertFalse(((a[..., 0] > 235) & (a[..., 1] < 40) & (a[..., 2] > 235)).any(), f'magenta t={t}')
            # au moins 50 couleurs différentes dans chaque cadre (dégradé, pas de plat)
            self.assertGreater(len(np.unique(a.reshape(-1, 3), axis=0)), 50, f'trop plat t={t}')

    def test_mew_dans_le_cadre_et_taille_raisonnable(self):
        # dans l'acte 2 (descente), Mew doit rester visible et de taille cohérente.
        for t in np.arange(9.5, 21.5, 1.0):
            x, y, sc, ang, *_ = B.mew_state(float(t))
            # taille de Mew (hauteur) entre 25 et 290 px
            A, _ = B.mew_sources()
            h = A.shape[0] * sc
            self.assertGreater(h, 25, f'Mew trop petit t={t}')
            self.assertLess(h, 300, f'Mew trop grand t={t}')
            # centre dans l'écran, avec marges
            self.assertTrue(80 < x < B.W - 80 and 60 < y < B.H - 60, (t, x, y))

    def test_mew_surgit_du_soleil_et_senvole(self):
        # petit au début (dans le soleil), puis gros vers t=7-9 s, puis s'éloigne.
        _, _, sc0, *_ = B.mew_state(1.0)
        _, _, sc7, *_ = B.mew_state(7.0)
        _, _, sc15, *_ = B.mew_state(15.0)
        _, _, sc27, *_ = B.mew_state(27.0)
        self.assertLess(sc0, 0.10)
        self.assertGreater(sc7, 0.30)
        self.assertLess(sc15, sc7)
        self.assertLess(sc27, 0.12)               # loin à la fin (presque hors cadre)

    def test_decor_vertical_existe(self):
        bg = B.background()
        self.assertEqual(bg.shape, (1376, 768, 3))
        # la caméra démarre en haut (ciel) et finit en bas (monde/village) : teinte dominante change
        top = bg[20:200].mean(axis=(0, 1))
        bot = bg[1200:1360].mean(axis=(0, 1))
        self.assertGreater(top[2], top[1])        # le ciel est plus bleu
        self.assertGreater(bot[1], bot[2])        # le bas est plus vert

    def test_petales_8_poses_et_taille(self):
        for s in B.PETAL_SIZES:
            for k in range(8):
                sp = B.petal_sprite(s, k)
                self.assertEqual(sp.mode, 'RGBA')
                self.assertLessEqual(max(sp.size), s * 2 + 4)
                # au moins un pixel opaque, un pixel transparent (pour tourner)
                a = np.array(sp)[..., 3]
                self.assertTrue((a > 0).any())
                self.assertTrue((a == 0).any())

    def test_jalons_sauvegardes(self):
        for t in M['jalons_s']:
            p = O / f'review/IMW3_t{t:05.1f}s.png'
            self.assertTrue(p.is_file(), f'manque jalon {p.name}')
            self.assertEqual(Image.open(p).size, (B.W, B.H))

    def test_video_existe_et_duree_correcte(self):
        import imageio
        v = O / 'IMW3_traversee.mp4'
        self.assertTrue(v.is_file())
        rd = imageio.get_reader(v)
        try:
            meta = rd.get_meta_data()
            n = rd.count_frames()
        finally:
            rd.close()
        self.assertEqual(n, B.N_FRAMES)
        self.assertAlmostEqual(float(meta['fps']), B.FPS, places=1)

    def test_manifest_complet_et_flags(self):
        for k in ('lot', 'asset', 'serie', 'format', 'actes', 'decor', 'mew', 'effets', 'jalons_s', 'reserves'):
            self.assertIn(k, M)
        self.assertFalse(M['art_approved'])
        self.assertFalse(M['runtime_tested'])
        self.assertTrue(M['deterministe'])
        self.assertEqual(M['asset'], 'IMW3')


if __name__ == '__main__':
    unittest.main()
