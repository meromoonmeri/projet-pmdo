"""Tests dédiés — intro animée de Mew (IMW1). Lancer : .venv/bin/python -m unittest source.intro_mew_v1.test_build -v (après build.py)."""
import importlib.util, json, unittest
from pathlib import Path
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
O = R / 'renders/intro_mew_v1'
spec = importlib.util.spec_from_file_location('imw1_build', HERE / 'build.py')
B = importlib.util.module_from_spec(spec); spec.loader.exec_module(B)
M = json.loads((O / 'manifest.json').read_text())


def video_frame(n):
    import imageio
    rd = imageio.get_reader(O / 'IMW1_intro_mew.mp4')
    try:
        return np.array(rd.get_data(n))
    finally:
        rd.close()


class Intro(unittest.TestCase):
    def test_chronologie(self):
        S = M['scenes']
        self.assertEqual(len(S), 11); self.assertEqual(len(B.SCENES), 11)
        self.assertEqual(S[0]['t_debut_s'], B.DUR_INTRO)
        for a, b in zip(S, S[1:]): self.assertEqual(a['t_fin_s'], b['t_debut_s'])           # cartes bout à bout, sans trou
        self.assertEqual(S[-1]['t_fin_s'], B.T_FINALE); self.assertEqual(B.T_END, B.T_FINALE + B.DUR_FINALE)
        self.assertEqual(M['format']['frames'], B.N_FRAMES); self.assertEqual(B.N_FRAMES, round(B.T_END * 30))
        self.assertEqual(len({s['carte_source'] for s in S}), 11)                           # 11 cartes toutes différentes
        for s in B.SCENES: self.assertTrue((R / 'renders' / s[1] / 'review').is_dir(), s[1])
        self.assertEqual([a['cle'] for a in M['actes']][0], 'ouverture_aube'); self.assertEqual(M['actes'][-1]['cle'], 'finale_doree')
        for k, (a, b) in enumerate(zip(B.TOD, B.TOD[1:])):
            self.assertLess(a[0], b[0]); self.assertTrue(0 <= a[3] <= 1)
            self.assertTrue(all(0 < c <= 1.0 for c in a[5]), k)
        self.assertEqual((B.TOD[0][0], B.TOD[-1][0]), (0.0, B.T_END))

    def test_mew_sprite(self):
        mew = B.mew_native(); cols = np.unique(mew[mew[..., 3] > 0][:, :3], axis=0)
        self.assertLessEqual(len(cols), 15); self.assertEqual(M['mew']['couleurs'], len(cols))   # profil sprite du projet : au plus 15 couleurs
        self.assertEqual(set(np.unique(mew[..., 3])), {0, 255})
        self.assertEqual(mew.shape[:2], (58, 66))
        f8 = B.mew_frames(8); f16 = B.mew_frames(16)
        for k in range(8): self.assertTrue((f8[k] == f16[2 * k]).all())                    # la boucle est exacte (pose 8 = pose 0)
        self.assertEqual(len({f.tobytes() for f in f8}), 8)                                # 8 poses distinctes
        for f in f8:
            self.assertTrue((f[:, 30:] == f8[0][:, 30:]).all())                           # seule la queue bouge (x < 30)
            sh = []                                                                        # décalage de chaque colonne par rapport à la queue d'origine
            for x in range(30):
                s0 = np.nonzero(np.pad(B.mew_native()[:, x, 3], (4, 4)))[0]; s1 = np.nonzero(f[:, x, 3])[0]
                sh.append(int(s1.min()) - int(s0.min()) if len(s0) and len(s1) else 0)
            self.assertLessEqual(max(abs(v) for v in sh), 3)
            self.assertTrue(all(abs(a - b) <= 2 for a, b in zip(sh, sh[1:])))              # le trait reste lié d'une colonne à l'autre
        used = {tuple(c) for f in f8 for c in f[f[..., 3] > 0][:, :3]}
        self.assertTrue(used <= {tuple(c) for c in cols})                                  # aucune couleur nouvelle

    def test_cadres_pixels_entiers_et_deterministes(self):
        for t in (3.0, 10.2, 27.0, 40.5, 52.0, 56.3, 60.0):
            a = B.render(t); self.assertEqual(a.shape, (288, 384, 3)); self.assertEqual(a.dtype, np.uint8)
            up = B.upscale(a); self.assertEqual(up.shape, (576, 768, 3))
            self.assertTrue((up[0::2, 0::2] == up[1::2, 1::2]).all() and (up[0::2, 1::2] == up[1::2, 0::2]).all())   # blocs 2 x 2
        self.assertTrue((B.render(20.2) == B.render(20.2)).all())
        self.assertFalse((B.render(20.2) == B.render(20.3)).all())                         # ça bouge

    def test_pas_de_magenta_et_pas_de_noir_plat(self):
        for t in np.linspace(0.8, B.T_END - 1.2, 25):
            a = B.render(float(t)).astype(int)
            self.assertFalse(((a[..., 0] > 235) & (a[..., 1] < 40) & (a[..., 2] > 235)).any(), t)
            self.assertGreater(len(np.unique(a.reshape(-1, 3), axis=0)), 30, t)

    def test_mew_toujours_visible_hors_transition(self):
        mew = B.mew_native(); body = tuple(int(v) for v in mew[40, 33, :3])
        for t in np.arange(1.0, B.T_END - 1.5, 1.1):
            t = float(t)
            if B.wall_progress(t) is not None: continue
            mx, my, ms = B.mew_pos(t)
            if B.DUR_INTRO <= t < B.T_FINALE: self.assertTrue(110 < mx < 150 and 130 < my < 150, (t, mx, my))   # à gauche du centre : la caméra avance devant lui
            mul = B.tod(t)[4] if t < B.T_FINALE else (1.0, 0.93, 0.80)
            col = np.clip(np.array(mew[(mew[..., 3] > 0)][:, :3]).astype(float) * np.array(mul), 0, 255)
            a = B.render(t).astype(int)
            y0, y1, x0, x1 = int(my - 40), int(my + 40), int(mx - 45), int(mx + 45)
            win = a[max(0, y0):y1, max(0, x0):x1]
            fur = np.array(tuple(int(round(v * m)) for v, m in zip((251, 177, 200), mul)))
            n = int((np.abs(win - fur).sum(2) <= 3).sum())
            self.assertGreater(n, 150 if ms > 0.9 else 30, (t, n))

    def test_mur_de_nuages_couvre_tout_a_la_frontiere(self):
        wall = B.sprites()['wall']; self.assertEqual(wall.shape, (288, 960, 4))
        wx = int(round(B.lerp(B.LW, -960, 0.5)))
        cover = wall[:, -wx:-wx + B.LW, 3] > 127
        self.assertTrue(cover.all())                                                       # écran entier couvert au moment du changement de carte
        for k in range(len(B.SCENES) + 1):
            b = B.DUR_INTRO + k * B.DUR_SCENE if k < len(B.SCENES) else B.T_FINALE
            self.assertIsNotNone(B.wall_progress(b)); self.assertAlmostEqual(B.wall_progress(b)[1], 0.5)
            self.assertIsNone(B.wall_progress(b + 1.0)); self.assertIsNone(B.wall_progress(b - 1.0))
            # avant et après le mur, les deux côtés montrent bien des contenus différents
            if 0 < k < len(B.SCENES):
                self.assertGreater(np.abs(B.render(b - 0.9).astype(int) - B.render(b + 0.9).astype(int)).mean(), 8)

    def test_soleil_ouverture_et_finale(self):
        sun = np.array([255, 248, 214])
        for t in (6.5, B.T_FINALE + 1.0, B.T_FINALE + 4.0):
            a = B.render(t); self.assertGreater(int((np.abs(a.astype(int) - sun).sum(2) <= 12).sum()), 400, t)
        a = B.render(0.6).astype(int)                                                      # à l'aube, le soleil est encore caché derrière la mer de nuages
        self.assertLess(int((np.abs(a - sun).sum(2) <= 12).sum()), 400)
        ys = [B.sky_act(6.0, 8.0, 'aube', 6.0)]                                           # le ciel de l'ouverture change de tons
        self.assertGreater(np.abs(B.sky_act(0.5, 8.0, 'aube', 0.5).astype(int) - ys[0].astype(int)).mean(), 20)

    def test_scene_source_fidele(self):
        # au milieu de la carte 'jungle' la fenêtre de scène (avant teinte, lueur, nuages) est bien un morceau de la carte d'origine
        i = 2; t = B.SCENE_T0[i] + 2.25
        sf = B.scene_frames(i); wx, wy = B.pan_window(i, t - B.SCENE_T0[i]); src = sf.at(t - B.SCENE_T0[i])[wy:wy + 288, wx:wx + 384].astype(float)
        out = B.render(t).astype(float); mul = np.array(B.tod(t)[4])
        ref = np.clip(src * mul, 0, 255)
        d = np.abs(out - ref).sum(2)
        self.assertGreater(float((d < 40).mean()), 0.72)                                   # ~28 % : Mew, ombres, nuages, lueur étagée
        self.assertEqual(M['scenes'][i]['carte_source'], 'entree_jungle_sud_nord_v1')

    def test_video_mp4(self):
        import imageio
        rd = imageio.get_reader(O / 'IMW1_intro_mew.mp4'); meta = rd.get_meta_data(); n = rd.count_frames(); rd.close()
        self.assertEqual(tuple(meta['size']), (768, 576)); self.assertAlmostEqual(meta['fps'], 30.0, delta=0.01)
        self.assertAlmostEqual(n, B.N_FRAMES, delta=2)
        self.assertLess((O / 'IMW1_intro_mew.mp4').stat().st_size, 16_000_000)
        for t in (5.0, 20.0, 45.0, 60.0):
            v = video_frame(int(round(t * 30))).astype(int)
            r = B.upscale(B.render(int(round(t * 30)) / 30)).astype(int)
            self.assertLess(float(np.abs(v - r).mean()), 6.0, t)                           # le mp4 est bien le rendu de ces instants (compression : écart moyen < 6)

    def test_manifeste_et_calques(self):
        self.assertFalse(M['art_approved']); self.assertFalse(M['runtime_tested']); self.assertTrue(M['deterministe'])
        self.assertIn('pas une map PMDO', ' '.join(M['reserves']))
        for n in ('IMW1_mew_vol_8poses.png', 'IMW1_mer_de_nuages.png', 'IMW1_mur_de_nuages_transition.png', 'IMW1_ciel_aube.png', 'IMW1_ciel_dore.png'):
            self.assertIn(n, M['calques']); self.assertTrue((O / 'calques' / n).is_file(), n)
        im = Image.open(O / 'calques/IMW1_mew_vol_8poses.png'); self.assertEqual(im.size, (8 * 66, 66))
        self.assertGreaterEqual(len(list((O / 'review').glob('IMW1_t*.png'))), 15)


if __name__ == '__main__':
    unittest.main()
