# -*- coding: utf-8 -*_

import os
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import argparse
import math
import pandas as pd
from scipy.interpolate import InterpolatedUnivariateSpline
from scipy.signal import savgol_filter, find_peaks
from scipy.special import expit
import numpy as np
from glob import glob
import urllib
from warnings import warn
from datetime import datetime
import tensorflow as tf
from time import time
from tabulate import tabulate
from PIL import Image
import re
import biquad

ROOT_DIR = os.path.abspath(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_F_MIN = 20
DEFAULT_F_MAX = 20000
DEFAULT_STEP = 1.01
DEFAULT_MAX_GAIN = 6.0
DEFAULT_TREBLE_F_LOWER = 6000.0
DEFAULT_TREBLE_F_UPPER = 8000.0
DEFAULT_TREBLE_MAX_GAIN = 0.0
DEFAULT_TREBLE_GAIN_K = 1.0
DEFAULT_BASS_BOOST = 0.0
DEFAULT_SMOOTHING_WINDOW_SIZE = 1 / 7
DEFAULT_SMOOTHING_ITERATIONS = 10
DEFAULT_TREBLE_SMOOTHING_WINDOW_SIZE = 1 / 5
DEFAULT_TREBLE_SMOOTHING_ITERATIONS = 100
DEFAULT_TILT = 0.0
DEFAULT_COMPENSATION_FILE_PATH = os.path.join(
    'innerfidelity',
    'resources',
    'innerfidelity_compensation_SBAF-Serious-brighter.csv'
)
BASS_BOOST_F_LOWER = 60
BASS_BOOST_F_UPPER = 200
GRAPHIC_EQ_STEP = 1.07


class FrequencyResponse:
    def __init__(self,
                 name=None,
                 frequency=None,
                 raw=None,
                 error=None,
                 smoothed=None,
                 error_smoothed=None,
                 equalization=None,
                 parametric_eq=None,
                 equalized_raw=None,
                 equalized_smoothed=None,
                 target=None):
        self.name = name.strip()

        self.frequency = self._init_data(frequency)
        if not len(self.frequency):
            self.frequency = self.generate_frequencies()

        self.raw = self._init_data(raw)
        self.smoothed = self._init_data(smoothed)
        self.error = self._init_data(error)
        self.error_smoothed = self._init_data(error_smoothed)
        self.equalization = self._init_data(equalization)
        self.parametric_eq = self._init_data(parametric_eq)
        self.equalized_raw = self._init_data(equalized_raw)
        self.equalized_smoothed = self._init_data(equalized_smoothed)
        self.target = self._init_data(target)

        self._sort()

    @staticmethod
    def _init_data(data):
        """Initializes data to a clean format. If None is passed and empty array is created. Non-numbers are removed."""
        data = data if data is not None else []
        data = [None if x is None or math.isnan(x) else x for x in data]
        data = np.array(data)
        return data

    def _sort(self):
        sorted_inds = self.frequency.argsort()
        self.frequency = self.frequency[sorted_inds]
        if len(self.raw):
            self.raw = self.raw[sorted_inds]
        if len(self.error):
            self.error = self.error[sorted_inds]
        if len(self.smoothed):
            self.smoothed = self.smoothed[sorted_inds]
        if len(self.error_smoothed):
            self.error_smoothed = self.error_smoothed[sorted_inds]
        if len(self.equalization):
            self.equalization = self.equalization[sorted_inds]
        if len(self.parametric_eq):
            self.parametric_eq = self.parametric_eq[sorted_inds]
        if len(self.equalized_raw):
            self.equalized_raw = self.equalized_raw[sorted_inds]
        if len(self.equalized_smoothed):
            self.equalized_smoothed = self.equalized_smoothed[sorted_inds]
        if len(self.target):
            self.target = self.target[sorted_inds]

    def reset(self,
              raw=False,
              smoothed=True,
              error=True,
              error_smoothed=True,
              equalization=True,
              parametric_eq=True,
              equalized_raw=True,
              equalized_smoothed=True,
              target=True):
        """Resets data."""
        if (
                (raw and len(self.raw)) or
                (smoothed and len(self.smoothed)) or
                (error and len(self.error)) or
                (error_smoothed and len(self.error_smoothed)) or
                (equalization and len(self.equalization)) or
                (parametric_eq and len(self.parametric_eq)) or
                (equalized_raw and len(self.equalized_raw)) or
                (equalized_smoothed and len(self.equalized_smoothed)) or
                (target and len(self.target))
        ):
            warn('Resetting data, existing results will be affected!')
        if raw:
            self.raw = self._init_data(None)
        if smoothed:
            self.smoothed = self._init_data(None)
        if error:
            self.error = self._init_data(None)
        if error_smoothed:
            self.error_smoothed = self._init_data(None)
        if equalization:
            self.equalization = self._init_data(None)
        if parametric_eq:
            self.parametric_eq = self._init_data(None)
        if equalized_raw:
            self.equalized_raw = self._init_data(None)
        if equalized_smoothed:
            self.equalized_smoothed = self._init_data(None)
        if target:
            self.target = self._init_data(None)

    @classmethod
    def read_from_csv(cls, file_path):
        """Reads data from CSV file and constructs class instance."""
        file_path = os.path.abspath(file_path)
        name = os.path.split(file_path)[-1].split('.')[0]

        df = pd.read_csv(file_path, sep=',', header=0)
        frequency = list(df['frequency']) if 'frequency' in df else None
        raw = list(df['raw']) if 'raw' in df else None
        error = list(df['error']) if 'error' in df else None
        smoothed = list(df['smoothed']) if 'smoothed' in df else None
        equalization = list(df['equalization']) if 'equalization' in df else None
        parametric_eq = list(df['parametric_eq']) if 'parametric_eq' in df else None
        equalized_raw = list(df['equalized_raw']) if 'equalized_raw' in df else None
        equalized_smoothed = list(df['equalized_smoothed']) if 'equalized_smoothed' in df else None
        target = list(df['target']) if 'target' in df else None

        return cls(
            name=name,
            frequency=frequency,
            raw=raw,
            error=error,
            smoothed=smoothed,
            equalization=equalization,
            parametric_eq=parametric_eq,
            equalized_raw=equalized_raw,
            equalized_smoothed=equalized_smoothed,
            target=target
        )

    def write_to_csv(self, file_path=None):
        """Writes data to files as CSV."""
        file_path = os.path.abspath(file_path)
        df = pd.DataFrame()
        if len(self.frequency):
            df['frequency'] = self.frequency
        if len(self.raw):
            df['raw'] = [x if x is not None else 'NaN' for x in self.raw]
        if len(self.error):
            df['error'] = [x if x is not None else 'NaN' for x in self.error]
        if len(self.smoothed):
            df['smoothed'] = [x if x is not None else 'NaN' for x in self.smoothed]
        if len(self.error_smoothed):
            df['error_smoothed'] = [x if x is not None else 'NaN' for x in self.error_smoothed]
        if len(self.equalization):
            df['equalization'] = [x if x is not None else 'NaN' for x in self.equalization]
        if len(self.parametric_eq):
            df['parametric_eq'] = [x if x is not None else 'NaN' for x in self.parametric_eq]
        if len(self.equalized_raw):
            df['equalized_raw'] = [x if x is not None else 'NaN' for x in self.equalized_raw]
        if len(self.equalized_smoothed):
            df['equalized_smoothed'] = [x if x is not None else 'NaN' for x in self.equalized_smoothed]
        if len(self.target):
            df['target'] = [x if x is not None else 'NaN' for x in self.target]
        df.to_csv(file_path, header=True, index=False, float_format='%.2f')

    def write_eqapo_graphic_eq(self, file_path):
        """Writes equalization graph to a file as Equalizer APO config."""
        file_path = os.path.abspath(file_path)

        fr = FrequencyResponse(name='hack', frequency=self.frequency, raw=self.equalization)
        fr.interpolate(f_min=DEFAULT_F_MIN, f_max=DEFAULT_F_MAX, f_step=GRAPHIC_EQ_STEP)

        with open(file_path, 'w') as f:
            s = '; '.join(['{f} {a:.1f}'.format(f=f, a=a) for f, a in zip(fr.frequency, fr.raw)])
            s = 'GraphicEQ: 10 -84; ' + s
            f.write(s)
        return s

    @staticmethod
    def _run_optimize_parametric_eq(frequency, target, target_loss=0.1, max_filters=None):
        # Reset graph to be able to run this again
        tf.reset_default_graph()
        # Sampling frequency
        fs = tf.constant(48000, name='f', dtype='float32')

        # Filter heavily and find peaks
        fr_target = FrequencyResponse(name='Filter Initialization', frequency=frequency, raw=target)
        fr_target.smoothen(window_size=1/7, iterations=1000)
        fr_target_pos = np.clip(fr_target.smoothed, a_min=0.0, a_max=None)
        peak_inds = find_peaks(fr_target_pos)[0]
        fr_target_neg = np.clip(-fr_target.smoothed, a_min=0.0, a_max=None)
        peak_inds = np.concatenate((peak_inds, find_peaks(fr_target_neg)[0]))
        peak_inds.sort()
        peak_inds = peak_inds[np.abs(fr_target.smoothed[peak_inds]) > 0.1]

        # Positive, dropping and first peak is positive \/\ -> 20 Hz to first peak
        # Positive, dropping and first peak is negative \ -> 20 Hz to zero crossing
        # Positive and raising /\ -> Nothing

        # Peak center frequencies and gains
        peak_fc = frequency[peak_inds].astype('float32')

        if peak_fc[0] > 80:
            # First peak is beyond 80Hz, add peaks to 20Hz and 60Hz
            peak_fc = np.concatenate((np.array([20, 60], dtype='float32'), peak_fc))
        elif peak_fc[0] > 40:
            # First peak is beyond 40Hz, add peak to 20Hz
            peak_fc = np.concatenate((np.array([20], dtype='float32'), peak_fc))

        # Gains at peak center frequencies
        interpolator = InterpolatedUnivariateSpline(np.log10(frequency), fr_target.smoothed, k=1)
        peak_g = interpolator(np.log10(peak_fc)).astype('float32')

        peak_fc_all = peak_fc
        peak_g_all = peak_g

        def remove_small_filters(min_gain):
            # Remove peaks with too little gain
            nonlocal peak_fc, peak_g
            peak_fc = peak_fc[np.abs(peak_g) > min_gain]
            peak_g = peak_g[np.abs(peak_g) > min_gain]

        def merge_filters():
            # Merge two filters which have small integral between them
            nonlocal peak_fc, peak_g
            # Form filter pairs, select only filters with equal gain sign
            pair_inds = []
            for j in range(len(peak_fc) - 1):
                if np.sign(peak_g[j]) == np.sign(peak_g[j+1]):
                    pair_inds.append(j)

            min_err = None
            min_err_ind = None
            for pair_ind in pair_inds:
                # Interpolate between the two points
                f_0 = peak_fc[pair_ind]
                g_0 = peak_g[pair_ind]
                i_0 = np.where(frequency == f_0)[0][0]
                f_1 = peak_fc[pair_ind+1]
                i_1 = np.where(frequency == f_1)[0][0]
                g_1 = peak_g[pair_ind]
                interp = InterpolatedUnivariateSpline(np.log10([f_0, f_1]), [g_0, g_1], k=1)
                line = interp(frequency[i_0:i_1+1])
                err = line - fr_target.smoothed[i_0:i_1+1]
                err = np.sqrt(np.mean(np.square(err)))  # Root mean squared error
                if min_err is None or err < min_err:
                    min_err = err
                    min_err_ind = pair_ind
            # Select smallest error if err < threshold
            if min_err < 0.3:
                # New filter
                c = peak_fc[min_err_ind] * np.sqrt(peak_fc[min_err_ind+1] / peak_fc[min_err_ind])
                c = frequency[np.argmin(np.abs(frequency - c))]
                g = np.mean([peak_g[min_err_ind], peak_g[min_err_ind+1]])
                # Remove filters
                peak_fc = np.delete(peak_fc, [min_err_ind, min_err_ind+1])
                peak_g = np.delete(peak_g, [min_err_ind, min_err_ind+1])
                # Add filter in-between
                peak_fc = np.insert(peak_fc, min_err_ind, c)
                peak_g = np.insert(peak_g, min_err_ind, g)
                return True
            return False  # No prominent filter pairs

        remove_small_filters(0.1)
        if max_filters is not None:
            if len(peak_fc) > max_filters:
                # Remove too small filters
                remove_small_filters(0.2)

            if len(peak_fc) > max_filters:
                # Try to remove some more
                remove_small_filters(0.33)

            # Merge filters if needed
            while merge_filters() and len(peak_fc) > max_filters:
                pass

            if len(peak_fc) > max_filters:
                # Remove smallest filters
                sorted_inds = np.flip(np.argsort(np.abs(peak_g)))
                sorted_inds = sorted_inds[:max_filters]
                peak_fc = peak_fc[sorted_inds]
                peak_g = peak_g[sorted_inds]

        # fr_target.plot_graph(show=False)
        fr_target.plot_graph(show=False)
        plt.plot(peak_fc_all, peak_g_all, 'o', color='red')
        plt.plot(peak_fc, peak_g, '.', color='limegreen')
        plt.legend(['Smoothed Target', 'Equalization Target', 'Before Reduction', 'After Reduction'])
        plt.show()

        n = n_pk = len(peak_fc)
        n_ls = n_hs = 0

        # Frequencies and target gain
        f = tf.constant(np.repeat(np.expand_dims(frequency, axis=0), n, axis=0), name='f', dtype='float32')
        eq_target = tf.constant(target, name='eq_target', dtype='float32')

        # Center frequencies
        fc = tf.get_variable('fc', initializer=np.expand_dims(peak_fc, axis=1), dtype='float32')

        # Q
        Q_init = np.ones([n_pk, 1], dtype='float32')
        Q = tf.get_variable('Q', initializer=np.ones([n, 1], dtype='float32') * Q_init, dtype='float32')

        # Gain
        gain = tf.get_variable('gain', initializer=np.expand_dims(peak_g, axis=1), dtype='float32')

        # Filter design

        # Low shelf filter
        # This is not used at the moment but is kept for future
        A = 10 ** (gain[:n_ls, :] / 40)
        w0 = 2 * np.pi * fc[:n_ls, :] / fs
        alpha = tf.sin(w0) / (2 * Q[:n_ls, :])

        a0_ls = ((A + 1) + (A - 1) * tf.cos(w0) + 2 * tf.sqrt(A) * alpha)
        a1_ls = (-(-2 * ((A - 1) + (A + 1) * tf.cos(w0))) / a0_ls)
        a2_ls = (-((A + 1) + (A - 1) * tf.cos(w0) - 2 * tf.sqrt(A) * alpha) / a0_ls)

        b0_ls = ((A * ((A + 1) - (A - 1) * tf.cos(w0) + 2 * tf.sqrt(A) * alpha)) / a0_ls)
        b1_ls = ((2 * A * ((A - 1) - (A + 1) * tf.cos(w0))) / a0_ls)
        b2_ls = ((A * ((A + 1) - (A - 1) * tf.cos(w0) - 2 * tf.sqrt(A) * alpha)) / a0_ls)

        # Peak filter
        A = 10 ** (gain[n_ls:n_ls+n_pk, :] / 40)
        w0 = 2 * np.pi * fc[n_ls:n_ls+n_pk, :] / fs
        alpha = tf.sin(w0) / (2 * Q[n_ls:n_ls+n_pk, :])

        a0_pk = (1 + alpha / A)
        a1_pk = -(-2 * tf.cos(w0)) / a0_pk
        a2_pk = -(1 - alpha / A) / a0_pk

        b0_pk = (1 + alpha * A) / a0_pk
        b1_pk = (-2 * tf.cos(w0)) / a0_pk
        b2_pk = (1 - alpha * A) / a0_pk

        # High self filter
        # This is not kept at the moment but kept for future
        A = 10 ** (gain[n_ls+n_pk:, :] / 40)
        w0 = 2 * np.pi * fc[n_ls+n_pk:, :] / fs
        alpha = tf.sin(w0) / (2 * Q[n_ls+n_pk:, :])

        a0_hs = (A + 1) - (A - 1) * tf.cos(w0) + 2 * tf.sqrt(A) * alpha
        a1_hs = -(2 * ((A - 1) - (A + 1) * tf.cos(w0))) / a0_hs
        a2_hs = -((A + 1) - (A - 1) * tf.cos(w0) - 2 * tf.sqrt(A) * alpha) / a0_hs

        b0_hs = (A * ((A + 1) + (A - 1) * tf.cos(w0) + 2 * tf.sqrt(A) * alpha)) / a0_hs
        b1_hs = (-2 * A * ((A - 1) + (A + 1) * tf.cos(w0))) / a0_hs
        b2_hs = (A * ((A + 1) + (A - 1) * tf.cos(w0) - 2 * tf.sqrt(A) * alpha)) / a0_hs

        # Concatenate all
        a0 = tf.concat([a0_ls, a0_pk, a0_hs], axis=0)
        a1 = tf.concat([a1_ls, a1_pk, a1_hs], axis=0)
        a2 = tf.concat([a2_ls, a2_pk, a2_hs], axis=0)
        b0 = tf.concat([b0_ls, b0_pk, b0_hs], axis=0)
        b1 = tf.concat([b1_ls, b1_pk, b1_hs], axis=0)
        b2 = tf.concat([b2_ls, b2_pk, b2_hs], axis=0)

        w = 2 * np.pi * f / fs
        phi = 4 * tf.sin(w / 2) ** 2

        a0 = 1.0
        a1 *= -1
        a2 *= -1

        # Equalizer frequency response
        eq_op = 10 * tf.log(
            (b0 + b1 + b2) ** 2 + (b0 * b2 * phi - (b1 * (b0 + b2) + 4 * b0 * b2)) * phi
        ) / tf.log(10.0) - 10 * tf.log(
            (a0 + a1 + a2) ** 2 + (a0 * a2 * phi - (a1 * (a0 + a2) + 4 * a0 * a2)) * phi
        ) / tf.log(10.0)
        eq_op = tf.reduce_sum(eq_op, axis=0)

        # Loss and optimizer
        loss = tf.reduce_mean(tf.square(eq_op - eq_target))
        learning_rate_value = 0.5
        decay = 0.9995
        learning_rate = tf.placeholder('float32', shape=(), name='learning_rate')
        train_step = tf.train.AdamOptimizer(learning_rate=learning_rate).minimize(loss)

        # Optimization loop
        t = time()
        min_loss = None
        threshold = 0.01
        momentum = 300
        bad_steps = 0
        with tf.Session() as sess:
            sess.run(tf.global_variables_initializer())
            for i in range(10000):
                step_loss, _ = sess.run([loss, train_step], feed_dict={learning_rate: learning_rate_value})
                if min_loss is None or step_loss < min_loss:
                    # Improvement, update model
                    _eq, _fc, _Q, _gain = sess.run([eq_op, fc, Q, gain])
                if min_loss is None or min_loss - step_loss > threshold:
                    # Loss improved
                    min_loss = step_loss
                    bad_steps = 0
                    if min_loss < target_loss:
                        # Good enough, stop optimizing
                        break
                else:
                    # No improvement, increment bad step counter
                    bad_steps += 1
                if bad_steps > momentum:
                    # Bad steps exceed maximum number of bad steps, break
                    break
                learning_rate_value = learning_rate_value * decay

        rmse = np.sqrt(min_loss)  # RMSE
        # print('Optimized {n} filters in {duration:.1f}s and achieved RMSE of {rmse:.2f}dB'.format(
        #     n=n,
        #     duration=time() - t,
        #     rmse=rmse,
        # ))

        # Remove filters with less than 0.1dB gain. Optimizer might produce these sometimes.
        sl = (np.abs(_gain) > 0.1)
        _fc = np.expand_dims(_fc[sl], axis=1)
        _Q = np.expand_dims(np.abs(_Q[sl]), axis=1)
        _gain = np.expand_dims(_gain[sl], axis=1)

        # Re-compute eq
        a0, a1, a2, b0, b1, b2 = biquad.peaking(_fc, _Q, _gain, fs=48000)
        frequency = np.repeat(np.expand_dims(frequency, axis=0), len(_fc), axis=0)
        _eq = np.sum(biquad.digital_coeffs(frequency, 48000, a0, a1, a2, b0, b1, b2), axis=0)

        return _eq, rmse, _fc, _Q, _gain

    def optimize_parametric_eq(self, max_filters=None):
        """Fits multiple biquad filters to equalization curve."""
        if not len(self.equalization):
            raise ValueError('Equalization has not been done yet.')

        eq, rmse, fc, Q, gain = self._run_optimize_parametric_eq(
            frequency=self.frequency,
            target=self.equalization,
            target_loss=0.1,
            max_filters=max_filters
        )

        self.parametric_eq = eq

        return np.hstack([fc, Q, gain])

    def write_eqapo_parametric_eq(self, file_path, filters):
        """Writes EqualizerAPO Parameteric eq settings to a file."""
        file_path = os.path.abspath(file_path)

        with open(file_path, 'w') as f:
            f.write('\n'.join(['Filter {i}: ON {type} Fc {fc:.0f} Hz Gain {gain:.1f} dB Q {Q:.2f}'.format(
                i=i+1,
                type='PK',
                fc=filters[i, 0],
                Q=filters[i, 1],
                gain=filters[i, 2]
            ) for i in range(len(filters))]))

    def _split_path(self, path):
        """Splits file system path into components."""
        folders = []
        while 1:
            path, folder = os.path.split(path)

            if folder != "":
                folders.append(folder)
            else:
                if path != "":
                    folders.append(path)

                break

        folders.reverse()
        return folders

    def write_readme(self, file_path, write_graphic_eq=False, write_parametric_eq=False):
        """Writes README.md with picture and Equalizer APO settings."""
        file_path = os.path.abspath(file_path)
        dir_path = os.path.dirname(file_path)
        model = self.name

        # Write model
        s = '# {}\n'.format(model)

        # Add GraphicEQ settings
        graphic_eq_path = os.path.join(dir_path, model + ' GraphicEQ.txt')
        if write_graphic_eq and os.path.isfile(graphic_eq_path):
            preamp = min(0.0, float(-np.max(self.equalization)))
            preamp = np.floor(preamp * 10) / 10 - 0.5

            # Read Graphig eq
            with open(graphic_eq_path, 'r') as f:
                graphic_eq_str = f.read().strip()

            # Produce text
            s += '''
            ### EqualizerAPO
            In case of using EqualizerAPO without any GUI, replace `C:\Program Files\EqualizerAPO\config\config.txt`
            with:
            ```
            Preamp: {preamp}dB
            {graphic_eq}
            ```
            
            ### HeSuVi
            In case of using HeSuVi, replace `C:\Program Files\EqualizerAPO\config\HeSuVi\eq.txt` and omit `Preamp:
            {f_preamp}dB` and instead set Global volume in the UI for both channels to **{i_preamp}**
            '''.format(
                preamp=preamp,
                graphic_eq=graphic_eq_str,
                f_preamp=preamp,
                i_preamp=int(preamp * 10)
            )

        # Add parametric EQ settings
        parametric_eq_path = os.path.join(dir_path, model + ' ParametricEQ.txt')
        if write_parametric_eq and os.path.isfile(parametric_eq_path):
            preamp = np.min([0.0, float(-np.max(self.parametric_eq))])
            # Subtract 0.5dB and round down with resolution of 0.5dB
            # This is done to protect from affect of potential removed < 0.1dB filters in optimization
            preamp = np.floor((preamp - 0.5) * 2) / 2

            # Read Parametric eq
            with open(parametric_eq_path, 'r') as f:
                parametric_eq_str = f.read().strip()

            # Filters as Markdown table
            filters = []
            for line in parametric_eq_str.split('\n'):
                type = line[line.index('ON')+3:line.index('Fc')-1]
                if type == 'PK':
                    type = 'Peaking'
                if type == 'LS':
                    type = 'Low Shelf'
                if type == 'HS':
                    type = 'High Shelf'
                fc = line[line.index('Fc')+3:line.index('Gain')-1]
                gain = line[line.index('Gain')+5:line.index('Q')-1]
                q = line[line.index('Q')+2:]
                filters.append([type, fc, q, gain])
            filters_table_str = tabulate(
                filters,
                headers=['Type', 'Fc', 'Q', 'Gain'],
                tablefmt='orgtbl'
            ).replace('+', '|').replace('|-', '|:')

            s += '''
            ### Peace
            In case of using Peace, click *Import* in Peace GUI and select `{model} ParametricEQ.txt`.
            
            ### Parametric EQs
            In case of using other parametric equalizer, apply preamp of **{preamp}dB** and build filters manually with
            these parameters:

            {filters_table}
            '''.format(
                model=model,
                preamp=preamp,
                parametric_eq=parametric_eq_str,
                filters_table=filters_table_str
            )

        # Write image link
        img_path = os.path.join(dir_path, model + '.png')
        if os.path.isfile(img_path):
            img_rel_path = os.path.relpath(img_path, ROOT_DIR)
            img_url = '/'.join(self._split_path(img_rel_path))
            img_url = 'https://raw.githubusercontent.com/jaakkopasanen/AutoEq/master/{}'.format(img_url)
            img_url = urllib.parse.quote(img_url, safe="%/:=&?~#+!$,;'@()*[]")
            s += '\n![]({})'.format(img_url)

        # Write file
        with open(file_path, 'w') as f:
            f.write(re.sub('\n[ \t]+', '\n', s).strip())

    @staticmethod
    def generate_frequencies(f_min=DEFAULT_F_MIN, f_max=DEFAULT_F_MAX, f_step=DEFAULT_STEP):
        freq_new = []
        # Frequencies from 20kHz down
        f = np.min([20000, f_max])
        while f > f_min:
            freq_new.append(int(round(f)))
            f = f / f_step
        # Frequencies from 20kHZ up
        f = np.min([20000, f_max])
        while f < f_max:
            freq_new.append(int(round(f)))
            f = f * f_step
        freq_new = sorted(set(freq_new))  # Remove duplicates and sort ascending
        return np.array(freq_new)

    def interpolate(self, f=None, f_step=DEFAULT_STEP, pol_order=1, f_min=DEFAULT_F_MIN, f_max=DEFAULT_F_MAX):
        """Interpolates missing values from previous and next value. Resets all but raw data."""
        # Remove None values
        i = 0
        while i < len(self.raw):
            if self.raw[i] is None:
                self.raw = np.delete(self.raw, i)
                self.frequency = np.delete(self.frequency, i)
            else:
                i += 1
        interpolator = InterpolatedUnivariateSpline(np.log10(self.frequency), self.raw, k=pol_order)

        if f is None:
            self.frequency = self.generate_frequencies(f_min=f_min, f_max=f_max, f_step=f_step)
        else:
            self.frequency = f
        self.raw = interpolator(np.log10(self.frequency))
        # Everything but raw data is affected by interpolating, reset them
        self.reset(raw=False)

    def calibrate(self, calibration):
        """Calibrates measurement to match calibration. Changes raw data."""
        self.raw -= calibration.raw
        # Everything but raw data is affected by calibrating, reset them
        self.reset(raw=False)

    def center(self):
        """Removed bias from frequency response."""
        interpolator = InterpolatedUnivariateSpline(np.log10(self.frequency), self.raw, k=1)
        diff = interpolator(np.log10(1000))
        self.raw -= diff
        if len(self.smoothed):
            self.smoothed -= diff
        # Everything but raw, smoothed and target is affected by centering, reset them
        self.reset(raw=False, smoothed=False, target=False)

    def _tilt(self, tilt=DEFAULT_TILT):
        """Creates a tilt for equalization.

        Args:
            tilt: Slope steepness in dB/octave

        Returns:
            Tilted data
        """
        # Center in logarithmic scale
        c = DEFAULT_F_MIN * np.sqrt(DEFAULT_F_MAX / DEFAULT_F_MIN)
        # N octaves above center
        n_oct = np.log2(self.frequency / c)
        return n_oct * tilt

    def _target(self, bass_boost=DEFAULT_BASS_BOOST, tilt=DEFAULT_TILT):
        """Creates target curve with bass boost as described by harman target response.

        Args:
            bass_boost: Bass boost in dB

        Returns:
            Target for equalization
        """
        bass_boost = self._sigmoid(
            f_lower=BASS_BOOST_F_LOWER,
            f_upper=BASS_BOOST_F_UPPER,
            a_normal=bass_boost,
            a_treble=0.0
        )
        tilt = self._tilt(tilt=tilt)
        return bass_boost + tilt

    def compensate(self, compensation, bass_boost=DEFAULT_BASS_BOOST, tilt=DEFAULT_TILT):
        """Calibrates raw frequency response data with compensation array. Doesn't change raw data."""
        # Copy and center compensation data
        compensation = FrequencyResponse(name='compensation', frequency=compensation.frequency, raw=compensation.raw)
        compensation.smoothen(
            window_size=DEFAULT_TREBLE_SMOOTHING_WINDOW_SIZE,
            iterations=DEFAULT_TREBLE_SMOOTHING_ITERATIONS
        )
        compensation.center()
        compensation.raw = compensation.smoothed
        compensation.smoothed = np.array([])
        # Set target
        self.target = compensation.raw + self._target(bass_boost=bass_boost, tilt=tilt)
        # Set error
        self.error = self.raw - self.target
        # Smoothed error and equalization results are affected by compensation, reset them
        self.reset(
            raw=False,
            smoothed=False,
            error=False,
            error_smoothed=True,
            equalization=True,
            parametric_eq=True,
            equalized_raw=True,
            equalized_smoothed=True,
            target=False
        )

    def _window_size(self, octaves):
        """Calculates moving average window size in indices from octaves."""
        # Octaves to coefficient
        k = 2 ** octaves
        # Calculate average step size in frequencies
        steps = []
        for i in range(1, len(self.frequency)):
            steps.append(self.frequency[i] / self.frequency[i - 1])
        step_size = sum(steps) / len(steps)
        # Calculate window size in indices
        # step_size^x = k  --> x = ...
        window_size = math.log(k) / math.log(step_size)
        # Half window size
        window_size = window_size
        # Round to integer to be usable as index
        window_size = round(window_size)
        if not window_size % 2:
            window_size += 1
        return window_size

    def _sigmoid(self, f_lower, f_upper, a_normal=0.0, a_treble=1.0):
        f_center = np.sqrt(f_upper / f_lower) * f_lower
        half_range = np.log10(f_upper) - np.log10(f_center)
        f_center = np.log10(f_center)
        a = expit((np.log10(self.frequency) - f_center) / (half_range / 4))
        a = a * -(a_normal - a_treble) + a_normal
        return a

    def _smoothen_data(self,
                       data,
                       window_size=DEFAULT_SMOOTHING_WINDOW_SIZE,
                       iterations=DEFAULT_SMOOTHING_ITERATIONS,
                       treble_window_size=None,
                       treble_iterations=None,
                       treble_f_lower=DEFAULT_TREBLE_F_LOWER,
                       treble_f_upper=DEFAULT_TREBLE_F_UPPER):
        """Smooths data.

        Args:
            window_size: Filter window size in octaves.
            iterations: Number of iterations to run the filter. Each new iteration is using output of previous one.
            treble_window_size: Filter window size for high frequencies.
            treble_iterations: Number of iterations for treble filter.
            treble_f_lower: Lower boundary of transition frequency region. In the transition region normal filter is \
                        switched to treble filter with sigmoid weighting function.
            treble_f_upper: Upper boundary of transition frequency reqion. In the transition region normal filter is \
                        switched to treble filter with sigmoid weighting function.
        """
        if None in self.frequency or None in data:
            # Must not contain None values
            raise ValueError('None values present, cannot smoothen!')

        # Normal filter
        y_normal = data
        for _ in range(iterations):
            y_normal = savgol_filter(y_normal, self._window_size(window_size), 2)

        # Treble filter
        y_treble = data
        for _ in range(treble_iterations):
            y_treble = savgol_filter(y_treble, self._window_size(treble_window_size), 2)

        # Transition weighted with sigmoid
        k_treble = self._sigmoid(treble_f_lower, treble_f_upper)
        k_normal = k_treble * -1 + 1
        return y_normal * k_normal + y_treble * k_treble

    def smoothen(self,
                 window_size=DEFAULT_SMOOTHING_WINDOW_SIZE,
                 iterations=DEFAULT_SMOOTHING_ITERATIONS,
                 treble_window_size=None,
                 treble_iterations=None,
                 treble_f_lower=DEFAULT_TREBLE_F_LOWER,
                 treble_f_upper=DEFAULT_TREBLE_F_UPPER):
        """Smooths data.

        Args:
            window_size: Filter window size in octaves.
            iterations: Number of iterations to run the filter. Each new iteration is using output of previous one.
            treble_window_size: Filter window size for high frequencies.
            treble_iterations: Number of iterations for treble filter.
            treble_f_lower: Lower boundary of transition frequency region. In the transition region normal filter is \
                        switched to treble filter with sigmoid weighting function.
            treble_f_upper: Upper boundary of transition frequency reqion. In the transition region normal filter is \
                        switched to treble filter with sigmoid weighting function.
        """
        if treble_f_upper <= treble_f_lower:
            raise ValueError('Upper transition boundary must be greater than lower boundary')

        # Use normal filter parameters for treble filter if treble filter parameters are not given
        if treble_window_size is None:
            treble_window_size = window_size
        if treble_iterations is None:
            treble_iterations = iterations

        # Smoothen raw data
        self.smoothed = self._smoothen_data(
            self.raw,
            window_size=window_size,
            iterations=iterations,
            treble_window_size=treble_window_size,
            treble_iterations=treble_iterations,
            treble_f_lower=treble_f_lower,
            treble_f_upper=treble_f_upper
        )

        if len(self.error):
            # Smoothen error data
            self.error_smoothed = self._smoothen_data(
                self.error,
                window_size=window_size,
                iterations=iterations,
                treble_window_size=treble_window_size,
                treble_iterations=treble_iterations,
                treble_f_lower=treble_f_lower,
                treble_f_upper=treble_f_upper
            )

        # Equalization is affected by smoothing, reset equalization results
        self.reset(
            raw=False,
            smoothed=False,
            error=False,
            error_smoothed=False,
            equalization=True,
            parametric_eq=True,
            equalized_raw=True,
            equalized_smoothed=True,
            target=False
        )

    def equalize(self,
                 max_gain=DEFAULT_MAX_GAIN,
                 smoothen=True,
                 treble_f_lower=DEFAULT_TREBLE_F_LOWER,
                 treble_f_upper=DEFAULT_TREBLE_F_UPPER,
                 treble_max_gain=DEFAULT_TREBLE_MAX_GAIN,
                 treble_gain_k=DEFAULT_TREBLE_GAIN_K):
        """Creates equalization curve and equalized curve.

        Args:
            max_gain: Maximum positive gain in dB
            smoothen: Smooth kinks caused by clipping gain to max gain?
            window_size: Smoothing average window size in octaves
            treble_f_lower: Lower frequency boundary for transition region between normal parameters and treble parameters
            treble_f_upper: Upper frequency boundary for transition reqion between normal parameters and treble parameters
            treble_max_gain: Maximum positive gain in dB in treble region
            treble_gain_k: Coefficient for treble gain, positive and negative. Useful for disbling or reducing \
                           equalization power in treble region. Defaults to 1.0 (not limited).
        """
        self.equalization = []
        self.equalized_raw = []

        if len(self.error_smoothed):
            error = self.error_smoothed
        elif len(self.error):
            error = self.error
        else:
            raise ValueError('Error data is missing. Call FrequencyResponse.compensate().')

        if None in error or None in self.equalization or None in self.equalized_raw:
            # Must not contain None values
            warn('None values detected during equalization, interpolating data with default parameters.')
            self.interpolate()

        # Invert with max gain clipping
        previous_clipped = False
        kink_inds = []

        # Max gain at each frequency
        max_gain = self._sigmoid(treble_f_lower, treble_f_upper, a_normal=max_gain, a_treble=treble_max_gain)
        gain_k = self._sigmoid(treble_f_lower, treble_f_upper, a_normal=1.0, a_treble=treble_gain_k)
        for i in range(len(error)):
            gain = - error[i] * gain_k[i]
            clipped = gain > max_gain[i]
            if previous_clipped != clipped:
                kink_inds.append(i)
            previous_clipped = clipped
            if clipped:
                gain = max_gain[i]
            self.equalization.append(gain)

        if len(kink_inds) and kink_inds[0] == 0:
            del kink_inds[0]

        if smoothen:
            # Smooth out kinks
            window_size = self._window_size(1 / 12)
            doomed_inds = set()
            for i in kink_inds:
                start = i - min(i, (window_size - 1) // 2)
                end = i + 1 + min(len(self.equalization) - i - 1, (window_size - 1) // 2)
                doomed_inds.update(range(start, end))
            doomed_inds = sorted(doomed_inds)

            for i in range(1, 3):
                if len(self.frequency) - i in doomed_inds:
                    del doomed_inds[doomed_inds.index(len(self.frequency) - i)]

            f = np.array([x for i, x in enumerate(self.frequency) if i not in doomed_inds])
            e = np.array([x for i, x in enumerate(self.equalization) if i not in doomed_inds])
            interpolator = InterpolatedUnivariateSpline(np.log10(f), e, k=2)
            self.equalization = interpolator(np.log10(self.frequency))
        else:
            self.equalization = np.array(self.equalization)

        # Equalized
        self.equalized_raw = self.raw + self.equalization
        if len(self.smoothed):
            self.equalized_smoothed = self.smoothed + self.equalization

    def plot_graph(self,
                   fig=None,
                   ax=None,
                   show=True,
                   raw=True,
                   error=True,
                   smoothed=True,
                   error_smoothed=True,
                   equalization=True,
                   parametric_eq=True,
                   equalized=True,
                   target=True,
                   file_path=None,
                   f_min=DEFAULT_F_MIN,
                   f_max=DEFAULT_F_MAX,
                   a_min=None,
                   a_max=None,
                   color='black'):
        """Plots frequency response graph."""
        if fig is None:
            fig, ax = plt.subplots()
        legend = []
        if not len(self.frequency):
            raise ValueError('\'frequency\' has no data!')
        if target and len(self.target):
            plt.plot(self.frequency, self.target, linewidth=5, color='lightblue')
            legend.append('Target')
        if smoothed and len(self.smoothed):
            plt.plot(self.frequency, self.smoothed, linewidth=5, color='lightgrey')
            legend.append('Raw Smoothed')
        if error_smoothed and len(self.error_smoothed):
            plt.plot(self.frequency, self.error_smoothed, linewidth=5, color='pink')
            legend.append('Error Smoothed')
        if raw and len(self.raw):
            plt.plot(self.frequency, self.raw, linewidth=1, color=color)
            legend.append('Raw')
        if error and len(self.error):
            plt.plot(self.frequency, self.error, linewidth=1, color='red')
            legend.append('Error')
        if parametric_eq and len(self.parametric_eq):
            plt.plot(self.frequency, self.parametric_eq, linewidth=5, color='lightgreen')
            legend.append('Parametric Eq')
        if equalization and len(self.equalization):
            plt.plot(self.frequency, self.equalization, linewidth=1, color='darkgreen')
            legend.append('Equalization')
        if equalized and len(self.equalized_raw) and not len(self.equalized_smoothed):
            plt.plot(self.frequency, self.equalized_raw, linewidth=1, color='magenta')
            legend.append('Equalized raw')
        if equalized and len(self.equalized_smoothed):
            plt.plot(self.frequency, self.equalized_smoothed, linewidth=1, color='blue')
            legend.append('Equalized smoothed')

        plt.xlabel('Frequency (Hz)')
        plt.semilogx()
        plt.xlim([f_min, f_max])
        plt.ylabel('Amplitude (dBr)')
        plt.ylim([a_min, a_max])
        plt.title(self.name)
        plt.legend(legend, fontsize=8)
        plt.grid(True, which='major')
        plt.grid(True, which='minor')
        ax.xaxis.set_major_formatter(ticker.StrMethodFormatter('{x:.0f}'))
        if file_path is not None:
            file_path = os.path.abspath(file_path)
            fig.savefig(file_path, dpi=120)
            im = Image.open(file_path)
            im = im.convert('P', palette=Image.ADAPTIVE, colors=60)
            im.save(file_path, optimize=True)
        if show:
            plt.show()
        return fig, ax

    @staticmethod
    def cli_args():
        """Parses command line arguments."""
        arg_parser = argparse.ArgumentParser()
        arg_parser.add_argument('--input_dir', type=str, required=True,
                                help='Path to input data directory. Will look for CSV files in the data directory and '
                                     'recursively in sub-directories.')
        arg_parser.add_argument('--output_dir', type=str, default=argparse.SUPPRESS,
                                help='Path to results directory. Will keep the same relative paths for files found'
                                     'in input_dir.')
        arg_parser.add_argument('--calibration', type=str, default=argparse.SUPPRESS,
                                help='File path to CSV containing calibration data. See `calibration` directory.')
        arg_parser.add_argument('--compensation', type=str, default=DEFAULT_COMPENSATION_FILE_PATH,
                                help='File path to CSV containing compensation curve. Compensation is necessary when '
                                     'equalizing because all input data is raw microphone data. See '
                                     'innerfidelity/resources and headphonecom/resources. '
                                     'Defaults to "{}".'.format(DEFAULT_COMPENSATION_FILE_PATH))
        arg_parser.add_argument('--equalize', action='store_true',
                                help='Will run equalization if this parameter exists, no value needed.')
        arg_parser.add_argument('--parametric_eq', action='store_true',
                                help='Will produce parametric eq settings if this parameter exists, no value needed.')
        arg_parser.add_argument('--max_filters', type=int, default=argparse.SUPPRESS,
                                help='Maximum number of filters for parametric EQ.')
        arg_parser.add_argument('--bass_boost', type=float, default=DEFAULT_BASS_BOOST,
                                help='Target gain for sub-bass in dB. Has flat response from 20 Hz to 60 Hz and a '
                                     'sigmoid slope down to 200 Hz. Defaults to {}.'.format(DEFAULT_BASS_BOOST))
        arg_parser.add_argument('--tilt', type=float, default=DEFAULT_TILT,
                                help='Target tilt in dB/octave. Positive value (upwards slope) will result in brighter '
                                     'frequency response and negative value (downwards slope) will result in darker '
                                     'frequency response. 1 dB/octave will produce nearly 10 dB difference in '
                                     'desired value between 20 Hz and 20 kHz. Tilt is applied with bass boost and both '
                                     'will affect the bass gain. Defaults to {}.'.format(DEFAULT_TILT))
        arg_parser.add_argument('--max_gain', type=float, default=DEFAULT_MAX_GAIN,
                                help='Maximum positive gain in equalization. Higher max gain allows to equalize deeper '
                                     'dips in  frequency response but will limit output volume if no analog gain is '
                                     'available because positive gain requires negative digital preamp equal to '
                                     'maximum positive gain. Defaults to {}.'.format(DEFAULT_MAX_GAIN))
        arg_parser.add_argument('--treble_f_lower', type=float, default=DEFAULT_TREBLE_F_LOWER,
                                help='Lower bound for transition region between normal and treble frequencies. Treble '
                                     'frequencies can have different smoothing, max gain and gain K. Defaults to '
                                     '{}.'.format(DEFAULT_TREBLE_F_LOWER))
        arg_parser.add_argument('--treble_f_upper', type=float, default=DEFAULT_TREBLE_F_UPPER,
                                help='Upper bound for transition region between normal and treble frequencies. Treble '
                                     'frequencies can have different smoothing, max gain and gain K. Defaults to '
                                     '{}.'.format(DEFAULT_TREBLE_F_UPPER))
        arg_parser.add_argument('--treble_max_gain', type=float, default=DEFAULT_TREBLE_MAX_GAIN,
                                help='Maximum positive gain for equalization in treble region. Defaults to '
                                     '{}.'.format(DEFAULT_TREBLE_MAX_GAIN))
        arg_parser.add_argument('--treble_gain_k', type=float, default=DEFAULT_TREBLE_GAIN_K,
                                help='Coefficient for treble gain, affects both positive and negative gain. Useful for '
                                     'disabling or reducing equalization power in treble region. Defaults to '
                                     '{}.'.format(DEFAULT_TREBLE_GAIN_K))
        arg_parser.add_argument('--show_plot', action='store_true',
                                help='Plot will be shown if this parameter exists, no value needed.')
        return vars(arg_parser.parse_args())

    @staticmethod
    def main(input_dir=None,
             output_dir=None,
             calibration=None,
             compensation=None,
             equalize=False,
             parametric_eq=False,
             max_filters=None,
             bass_boost=DEFAULT_BASS_BOOST,
             tilt=DEFAULT_TILT,
             max_gain=DEFAULT_MAX_GAIN,
             treble_f_lower=DEFAULT_TREBLE_F_LOWER,
             treble_f_upper=DEFAULT_TREBLE_F_UPPER,
             treble_max_gain=DEFAULT_TREBLE_MAX_GAIN,
             treble_gain_k=DEFAULT_TREBLE_GAIN_K,
             show_plot=False):
        """Parses files in input directory and produces equalization results in output directory."""
        if parametric_eq and not equalize:
            raise ValueError('equalize must be True when parametric_eq is True.')

        if calibration:
            # Creates FrequencyReponse for compensation data
            calibration_path = os.path.abspath(calibration)
            calibration = FrequencyResponse.read_from_csv(calibration_path)
            calibration.interpolate()
            calibration.center()

        if compensation:
            # Creates FrequencyReponse for compensation data
            compensation_path = os.path.abspath(compensation)
            compensation = FrequencyResponse.read_from_csv(compensation_path)
            compensation.interpolate()
            compensation.center()

        # Dir paths to absolute
        input_dir = os.path.abspath(input_dir)
        output_dir = os.path.abspath(output_dir)
        glob_files = glob(os.path.join(input_dir, '**', '*.csv'), recursive=True)
        if len(glob_files) == 0:
            warn('No CSV files found in "{}"'.format(input_dir))
            return

        readme_path = os.path.join(output_dir, 'README.md')
        readme_occupied = False

        for file_path in glob_files:
            # Read data from input file
            fr = FrequencyResponse.read_from_csv(file_path)

            # Copy relative path to output directory
            relative_path = os.path.relpath(file_path, input_dir)
            file_path = os.path.join(output_dir, relative_path)
            dir_path = os.path.dirname(file_path)
            if not os.path.isdir(dir_path):
                os.makedirs(dir_path, exist_ok=True)

            # Interpolate to standard frequency vector
            fr.interpolate()

            if calibration is not None:
                # Calibrate
                fr.calibrate(calibration)

            # Center by 1kHz
            fr.center()

            if compensation is not None:
                # Compensate
                fr.compensate(compensation, bass_boost=bass_boost, tilt=tilt)

            # Smooth data
            fr.smoothen(
                window_size=DEFAULT_SMOOTHING_WINDOW_SIZE,
                iterations=DEFAULT_SMOOTHING_ITERATIONS,
                treble_window_size=DEFAULT_TREBLE_SMOOTHING_WINDOW_SIZE,
                treble_iterations=DEFAULT_TREBLE_SMOOTHING_ITERATIONS,
                treble_f_lower=treble_f_lower,
                treble_f_upper=treble_f_upper
            )

            # Equalize
            if equalize:
                fr.equalize(
                    max_gain=max_gain,
                    smoothen=True,
                    treble_f_lower=treble_f_lower,
                    treble_f_upper=treble_f_upper,
                    treble_max_gain=treble_max_gain,
                    treble_gain_k=treble_gain_k
                )
                if parametric_eq:
                    # Get the filters
                    filters = fr.optimize_parametric_eq(max_filters=max_filters)

            if output_dir:
                if equalize:
                    # Write EqualizerAPO GraphicEq settings to file
                    fr.write_eqapo_graphic_eq(file_path.replace('.csv', ' GraphicEQ.txt'))
                    if parametric_eq:
                        # Write ParametricEq settings to file
                        fr.write_eqapo_parametric_eq(file_path.replace('.csv', ' ParametricEQ.txt'), filters)
                    print('Equalized "{}"'.format(fr.name))

                # Write results to CSV file
                fr.write_to_csv(file_path)
                # Write plots to file and optionally display them
                fig, ax = fr.plot_graph(
                    show=show_plot,
                    file_path=file_path.replace('.csv', '.png'),
                )
                plt.close(fig)

                # Write README.md
                _readme_path = os.path.join(dir_path, 'README.md')
                fr.write_readme(_readme_path, write_graphic_eq=equalize, write_parametric_eq=parametric_eq)
                if _readme_path == readme_path:
                    readme_occupied = True

            elif show_plot:
                fig, ax = fr.plot_graph(show=show_plot)
                plt.close(fig)

        lines = ['# Run {}'.format(datetime.now().isoformat())]
        lines.append('There results were obtained with parameters:')
        lines.append('* `--input_dir="{}"`'.format(os.path.relpath(input_dir, ROOT_DIR)))
        lines.append('* `--output_dir="{}"`'.format(os.path.relpath(output_dir, ROOT_DIR)))
        if calibration is not None:
            lines.append('* `--calibration="{}"`'.format(os.path.relpath(calibration_path, ROOT_DIR)))
        if compensation is not None:
            lines.append('* `--compensation="{}"`'.format(os.path.relpath(compensation_path, ROOT_DIR)))
        lines.append('* `--bass_boost={}`'.format(bass_boost))
        lines.append('* `--tilt={}`'.format(tilt))
        lines.append('* `--max_gain={}`'.format(max_gain))
        lines.append('* `--treble_f_lower={}`'.format(treble_f_lower))
        lines.append('* `--treble_f_upper={}`'.format(treble_f_upper))
        lines.append('* `--treble_max_gain={}`'.format(treble_max_gain))
        lines.append('* `--treble_gain_k={}`'.format(treble_gain_k))

        # Write parameters to run README.md
        if readme_occupied:
            # Directory already contains a README.md written for a single headphone
            # Add to the end of the README
            with open(readme_path, 'a') as f:
                f.write('\n' + '\n'.join(lines))
        else:
            # README.md doesn't exist or old README.md from previous run, safe to overwrite
            with open(readme_path, 'w') as f:
                f.write('\n'.join(lines))


if __name__ == '__main__':
    FrequencyResponse.main(**FrequencyResponse.cli_args())
