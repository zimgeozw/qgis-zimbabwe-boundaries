# Zimbabwe Boundaries (QGIS plugin)

Zimbabwe administrative boundaries in one click, with no internet connection needed.

| Level | Layer | Features | Main fields |
|---|---|---|---|
| 0 | Country | 1 | country, pcode |
| 1 | Provinces | 10 | province, prov_pcode |
| 2 | Districts | 91 | district, dist_pcode, province, prov_pcode |
| 3 | Wards (2018, old boundaries) | 1,961 | ward, ward_name, ward_pcode, district, dist_pcode, province, prov_pcode |

Every layer also has area_km2 (ellipsoidal), valid_on and source.

## Install
QGIS > Plugins > Manage and Install Plugins > Install from ZIP > choose `zimbabwe_boundaries.zip` > Install Plugin.
The tool appears on the toolbar and under Vector > Zimbabwe boundaries.

## Use
1. Tick the levels you need.
2. Optionally limit to some provinces and districts.
3. Choose the coordinate system (WGS 84, UTM 35S, UTM 36S or any other).
4. Add to the map and/or save to a folder as Shapefile, GeoPackage, GeoJSON or KML, optionally zipped.

From the QGIS Python console:

    from zimbabwe_boundaries import core
    wards = core.make_layer(3, provinces=['Manicaland'], districts=['Mutare'])
    core.save_layers([wards], r'C:\GIS\out', 'ESRI Shapefile')

## Data source and licence
Zimbabwe National Statistics Agency (ZIMSTAT) and OCHA ROSEA, Common Operational Dataset of administrative
boundaries (COD-AB), valid from 11 September 2018, published on the Humanitarian Data Exchange
(data.humdata.org, dataset "Zimbabwe - Subnational Administrative Boundaries"). Licence: CC BY-IGO.
Credit the source when you publish maps made with these boundaries.

The wards are the 2018 ward boundaries, which are older than the latest ward delimitation. Check them against
current Zimbabwe Electoral Commission ward maps before using them for electoral or ward-level planning work.

## Plugin
Map Tech (Pvt) Ltd t/a Zimgeo, 12th Floor, Joina City, Harare. aldridge@zimgeo.co.zw, +263 719 751 574.
Plugin code licensed under the GNU General Public License v2 or later.
