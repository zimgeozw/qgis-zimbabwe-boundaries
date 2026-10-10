"""Build the plugin's GeoPackage from the OCHA/ZIMSTAT COD-AB shapefiles (2018-09-11)."""
import sys, os
from qgis.core import (QgsApplication, QgsVectorLayer, QgsFields, QgsField, QgsFeature, QgsVectorFileWriter, QgsDistanceArea,
                       QgsCoordinateReferenceSystem, QgsCoordinateTransformContext, QgsWkbTypes)
from qgis.PyQt.QtCore import QVariant
QgsApplication.setPrefixPath('/usr', True); app = QgsApplication([], False); app.initQgis()
src, out = sys.argv[1], sys.argv[2]
if os.path.exists(out): os.remove(out)
shp = lambda l: f'{src}/zwe_admbnda_adm{l}_zimstat_ocha_20180911/zwe_admbnda_adm{l}_zimstat_ocha_20180911.shp'
da = QgsDistanceArea(); da.setEllipsoid('WGS84'); da.setSourceCrs(QgsCoordinateReferenceSystem('EPSG:4326'), QgsCoordinateTransformContext())
S, D = QVariant.String, QVariant.Double
specs = {
 0: ('zwe_level0_country', [('country', S), ('pcode', S)], lambda f: ['Zimbabwe', f['ADM0_PCODE']], 'ADM0_EN'),
 1: ('zwe_level1_provinces', [('province', S), ('prov_pcode', S), ('country', S)], lambda f: [f['ADM1_EN'], f['ADM1_PCODE'], 'Zimbabwe'], 'ADM1_PCODE'),
 2: ('zwe_level2_districts', [('district', S), ('dist_pcode', S), ('province', S), ('prov_pcode', S), ('country', S)],
     lambda f: [f['ADM2_EN'], f['ADM2_PCODE'], f['ADM1_EN'], f['ADM1_PCODE'], 'Zimbabwe'], 'ADM2_PCODE'),
 3: ('zwe_level3_wards_2018', [('ward', S), ('ward_name', S), ('ward_pcode', S), ('district', S), ('dist_pcode', S), ('province', S), ('prov_pcode', S), ('country', S)],
     lambda f: [str(f['ADM3_EN']), 'Ward %s' % f['ADM3_EN'], f['ADM3_PCODE'], f['ADM2_EN'], f['ADM2_PCODE'], f['ADM1_EN'], f['ADM1_PCODE'], 'Zimbabwe'], 'ADM3_PCODE'),
}
for lvl, (name, flds, attrs, sortkey) in specs.items():
    lyr = QgsVectorLayer(shp(lvl), name, 'ogr'); assert lyr.isValid(), shp(lvl)
    fields = QgsFields()
    for n, t in flds + [('area_km2', D), ('valid_on', S), ('source', S)]: fields.append(QgsField(n, t, '', 60 if t == S else 12, 0 if t == S else 2))
    o = QgsVectorFileWriter.SaveVectorOptions(); o.driverName = 'GPKG'; o.layerName = name
    o.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer if os.path.exists(out) else QgsVectorFileWriter.CreateOrOverwriteFile
    w = QgsVectorFileWriter.create(out, fields, QgsWkbTypes.MultiPolygon, QgsCoordinateReferenceSystem('EPSG:4326'), QgsCoordinateTransformContext(), o)
    n = 0; bad = 0
    for f in sorted(lyr.getFeatures(), key=lambda f: str(f[sortkey])):
        g = f.geometry()
        if not g.isGeosValid():
            g = g.makeValid(); bad += 1
        g.convertToMultiType()
        nf = QgsFeature(fields); nf.setGeometry(g)
        nf.setAttributes(attrs(f) + [round(da.measureArea(g) / 1e6, 2), '2018-09-11', 'ZIMSTAT, OCHA ROSEA (COD-AB)'])
        w.addFeature(nf); n += 1
    del w
    print(name, n, 'repaired', bad)
