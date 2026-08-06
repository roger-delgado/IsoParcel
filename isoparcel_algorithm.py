# -*- coding: utf-8 -*-
"""
IsoParcel - Equitable polygon subdivision algorithm for QGIS Processing.
Copyright (C) 2026 Roger Delgado Alcívar

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""

from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterNumber,
    QgsProcessingParameterFeatureSink,
    QgsGeometry,
    QgsFeature,
    QgsFields,
    QgsField,
    QgsWkbTypes,
    QgsFeatureSink,
)
from qgis.PyQt.QtCore import QCoreApplication, QVariant
from shapely.geometry import box
from shapely.affinity import rotate
from shapely import wkt
import numpy as np


class IsoParcelAlgorithm(QgsProcessingAlgorithm):
    INPUT = 'INPUT'
    ROWS = 'ROWS'
    COLS = 'COLS'
    TOLERANCE = 'TOLERANCE'
    MAX_ITER = 'MAX_ITER'
    OUTPUT = 'OUTPUT'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return IsoParcelAlgorithm()

    def name(self):
        return 'isoparcel'

    def displayName(self):
        return self.tr('IsoParcel')

    def group(self):
        return self.tr('Subdivision')

    def groupId(self):
        return 'subdivision'

    def shortHelpString(self):
        return self.tr(
            "Partitions input polygons into equal-area parcels using "
            "configurable row*column grids. Includes automatic topological "
            "repair and handles multipart geometries safely."
        )

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT,
                self.tr('Input polygon layer'),
                [QgsProcessing.TypeVectorPolygon]
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.ROWS,
                self.tr('Number of rows'),
                QgsProcessingParameterNumber.Integer,
                defaultValue=2,
                minValue=1,
                maxValue=50
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.COLS,
                self.tr('Number of columns'),
                QgsProcessingParameterNumber.Integer,
                defaultValue=2,
                minValue=1,
                maxValue=50
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.TOLERANCE,
                self.tr('Area tolerance (m²)'),
                QgsProcessingParameterNumber.Double,
                defaultValue=0.01,
                minValue=0.001,
                maxValue=10.0
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.MAX_ITER,
                self.tr('Max iterations per cut'),
                QgsProcessingParameterNumber.Integer,
                defaultValue=25,
                minValue=10,
                maxValue=100
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr('Subdivided parcels')
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        rows = self.parameterAsInt(parameters, self.ROWS, context)
        cols = self.parameterAsInt(parameters, self.COLS, context)
        tolerance = self.parameterAsDouble(parameters, self.TOLERANCE, context)
        max_iter = self.parameterAsInt(parameters, self.MAX_ITER, context)

        # Output keeps original attributes plus parent/index tracking fields.
        fields = QgsFields()
        for field in source.fields():
            fields.append(field)
        fields.append(QgsField('parent_id', QVariant.Int))
        fields.append(QgsField('parcel_idx', QVariant.Int))

        (sink, dest_id) = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            fields,
            QgsWkbTypes.Polygon,
            source.sourceCrs()
        )

        total = 100.0 / source.featureCount() if source.featureCount() else 100
        current = 0

        for feat in source.getFeatures():
            if feedback.isCanceled():
                break
            try:
                parcels = self._process_geometry(
                    feat.geometry(), rows, cols, tolerance, max_iter
                )
                for idx, p_geom in enumerate(parcels):
                    out_feat = QgsFeature(fields)
                    out_feat.setGeometry(p_geom)
                    for i, field in enumerate(source.fields()):
                        out_feat.setAttribute(i, feat.attribute(i))
                    out_feat.setAttribute('parent_id', feat.id())
                    out_feat.setAttribute('parcel_idx', idx + 1)
                    sink.addFeature(out_feat, QgsFeatureSink.FastInsert)
            except Exception as e:
                # Skip unrecoverable geometries without aborting the whole run.
                feedback.pushWarning(f"IsoParcel: Feature {feat.id()} failed: {str(e)}")
            feedback.setProgress(int(current * total))
            current += 1

        return {self.OUTPUT: dest_id}

    def _clean_geometry(self, qgs_geom: QgsGeometry) -> QgsGeometry:
        # Repair self-intersections and other topology errors before cutting.
        if not qgs_geom.isGeosValid():
            cleaned = qgs_geom.makeValid()
            if cleaned.isGeosValid():
                return cleaned
            return qgs_geom.buffer(0)
        return qgs_geom

    def _get_orientation_angle(self, qgs_geom: QgsGeometry) -> float:
        # Align the longest/base edge to the x-axis so row/column cuts follow
        # the polygon's natural orientation rather than the map grid.
        if qgs_geom.isMultipart():
            parts = qgs_geom.asGeometryCollection()
            qgs_geom = max(parts, key=lambda g: g.area())
        pts = list(qgs_geom.asPolygon()[0])
        base = sorted(pts, key=lambda p: p[1])[:2]
        if len(base) < 2:
            return 0.0
        return np.degrees(np.arctan2(base[1][1] - base[0][1], base[1][0] - base[0][0]))

    def _binary_cut(self, shapely_poly, n_parts, axis='y', max_iter=25, tol=0.01):
        # Binary search on the cut position along the given axis until the
        # cumulative sliced area matches the target equal-area fraction.
        minx, miny, maxx, maxy = shapely_poly.bounds
        atot = shapely_poly.area
        cuts, iters = [], []
        for i in range(1, n_parts):
            target = atot * (i / n_parts)
            low, high = (miny, maxy) if axis == 'y' else (minx, maxx)
            bc, ic = high, 0
            for _ in range(max_iter):
                ic += 1
                mid = (low + high) / 2
                cb = box(minx, miny, maxx, mid) if axis == 'y' else box(minx, miny, mid, maxy)
                inter = shapely_poly.intersection(cb)
                if inter.is_empty or inter.area == 0:
                    inter = box(0, 0, 0, 0)
                if inter.area < target:
                    low = mid
                else:
                    high = mid
                    bc = mid
                if abs(inter.area - target) / max(target, 1e-9) < 1e-6:
                    break
            cuts.append(bc)
            iters.append(ic)
        cuts.sort()

        # Slice the polygon at the resolved cut positions into ordered pieces.
        pieces, prev, lim = [], (miny if axis == 'y' else minx), (maxy if axis == 'y' else maxx)
        for cv in cuts:
            sb = box(minx, prev, maxx, cv) if axis == 'y' else box(prev, miny, cv, maxy)
            pc = shapely_poly.intersection(sb)
            if not pc.is_empty and pc.area > tol:
                if pc.geom_type == 'MultiPolygon':
                    pc = sorted(list(pc.geoms), key=lambda k: k.area, reverse=True)[0]
                pieces.append(pc)
            prev = cv
        lb = box(minx, prev, maxx, lim) if axis == 'y' else box(prev, miny, lim, maxy)
        lp = shapely_poly.intersection(lb)
        if not lp.is_empty and lp.area > tol:
            if lp.geom_type == 'MultiPolygon':
                lp = sorted(list(lp.geoms), key=lambda k: k.area, reverse=True)[0]
            pieces.append(lp)
        return pieces, np.mean(iters) if iters else 0

    def _process_geometry(self, qgs_geom: QgsGeometry, rows: int, cols: int,
                           tolerance: float, max_iter: int):
        clean_geom = self._clean_geometry(qgs_geom)
        if clean_geom.isEmpty() or not clean_geom.isGeosValid():
            raise ValueError("Invalid geometry after cleaning.")
        if clean_geom.isMultipart():
            clean_geom = max(clean_geom.asGeometryCollection(), key=lambda g: g.area())

        shapely_poly = wkt.loads(clean_geom.asWkt())
        angle = self._get_orientation_angle(clean_geom)
        centroid = shapely_poly.centroid

        # Rotate to the base orientation, cut rows then columns, then rotate back.
        rotated = rotate(shapely_poly, -angle, origin=centroid)
        strips, _ = self._binary_cut(rotated, rows, axis='y', max_iter=max_iter, tol=tolerance)
        if not strips:
            raise ValueError("Could not generate row cuts.")

        parcels = []
        for strip in strips:
            col_pieces, _ = self._binary_cut(strip, cols, axis='x', max_iter=max_iter, tol=tolerance)
            for p in col_pieces:
                parcels.append(rotate(p, angle, origin=centroid))

        return [QgsGeometry.fromWkt(p.wkt) for p in parcels]