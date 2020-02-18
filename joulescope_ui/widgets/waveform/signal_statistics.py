# Copyright 2019 Jetperch LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from pyqtgraph.Qt import QtGui, QtCore
from joulescope.units import unit_prefix, three_sig_figs
from joulescope.stream_buffer import single_stat_to_api
from joulescope_ui.ui_util import rgba_to_css, font_to_css
import numpy as np
import pyqtgraph as pg


STYLE_DEFAULT = 'color: #FFF'


def _si_format(names, values, units):
    results = []
    if units is None:
        units = ''
    if len(values):
        values = np.array(values)
        max_value = float(np.max(np.abs(values)))
        _, prefix, scale = unit_prefix(max_value)
        scale = 1.0 / scale
        if not len(prefix):
            prefix = '&nbsp;'
        units_suffix = f'{prefix}{units}'
        for lbl, v in zip(names, values):
            v *= scale
            if abs(v) < 0.000005:  # minimum display resolution
                v = 0
            v_str = ('%+6f' % v)[:8]
            results.append('%s=%s %s' % (lbl, v_str, units_suffix))
    return results


def si_format(labels):
    results = []
    if not len(labels):
        return results
    units = None
    values = []
    names = []
    for name, d in labels.items():
        value = d['value']
        if name == 'σ2':
            name = 'σ'
            value = np.sqrt(value)
        if d['units'] != units:
            results.extend(_si_format(names, values, units))
            units = d['units']
            values = [value]
            names = [name]
        else:
            values.append(value)
            names.append(name)
    results.extend(_si_format(names, values, units))
    return results


def html_format(results, x=None, style=None):
    if style is None:
        style = STYLE_DEFAULT
    if x is None:
        values = []
    else:
        values = ['t=%.6f' % (x, )]
    values += results

    body = '<br/>'.join(results)
    return f'<div><span style="{style}">{body}</span></div>'


class SignalStatistics(pg.GraphicsWidget):

    def __init__(self, parent=None, units=None, cmdp=None):
        pg.GraphicsWidget.__init__(self, parent=parent)
        self._units = units
        self.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        self._label = QtGui.QGraphicsTextItem(self)
        self._label.setVisible(True)
        self._value_cache = None
        self._cmdp = cmdp

        labels = single_stat_to_api(-0.000000001, 0.000001, -0.001, 0.001, self._units)
        txt_result = si_format(labels)
        self.data_update(txt_result)
        cmdp.subscribe('Widgets/Waveform/Statistics/font', self._on_font, update_now=True)
        cmdp.subscribe('Widgets/Waveform/Statistics/font-color', self._on_font_color, update_now=True)
        self._resize()
        pg.GraphicsWidget.show(self)

    def _resize(self):
        self._label.adjustSize()
        b = self._label.boundingRect()
        self.setMinimumHeight(b.height())
        self.setMinimumWidth(b.width())
        self.adjustSize()

    def _on_font(self, topic, value):
        self._data_update(*self._value_cache)
        font = QtGui.QFont()
        font.fromString(value)
        self._label.setFont(font)
        self._resize()

    def _on_font_color(self, topic, value):
        self._data_update(*self._value_cache)

    def close(self):
        self.scene().removeItem(self._label)
        self._label = None
        self._value_cache = None

    def data_clear(self):
        self._value_cache = None
        self._label.setHtml(f'<html><body></body></html>')

    def _data_update(self, results, x):
        font_color = rgba_to_css(self._cmdp['Widgets/Waveform/Statistics/font-color'])
        style = f'color: {font_color};'
        html = html_format(results, x=x, style=style)
        self._label.setHtml(html)

    def data_update(self, results, x=None):
        self._value_cache = (results, x)
        self._data_update(results, x)


class SignalMarkerStatistics(pg.TextItem):

    def __init__(self):
        pg.TextItem.__init__(self)

    def computing(self):
        self.setHtml(f'<html><body></body></html>')

    def move(self, vb, xv=None):
        if vb is not None:
            if xv is None:
                xv = self.pos().x()
            ys = vb.geometry().top()
            yv = vb.mapSceneToView(pg.Point(0.0, ys)).y()
            self.setPos(pg.Point(xv, yv))

    def data_update(self, vb, xv, labels):
        if labels is None or not len(labels):
            html = '<p>No data</p>'
        else:
            txt_result = si_format(labels)
            html = html_format(txt_result, x=xv)
        self.setHtml(html)
