# IsoParcel

Equitable polygon subdivision into configurable row*column grids with automatic topological cleaning.

## Description
IsoParcel partitions input polygon layers into equal-area parcels using an adaptive orthogonal cutting algorithm with binary search convergence. It automatically repairs self-intersections, handles multipart geometries safely, and guarantees area equity (CV <0.01%) for cadastral, agricultural, and experimental design workflows.

**Concept initiated**: 2026-05-15

## Features
- Subdivides polygons into N×M parcels with mathematically controlled area equity
- Automatic repair of self-intersections and degenerate vertices (`makeValid` + `buffer(0)`)
- Safe handling of MultiPolygon inputs (processes largest part)
- Integrated into QGIS Processing Toolbox (supports batch processing and graphical models)
- Configurable tolerance and iteration limits for precision control

## Requirements
- QGIS 3.22 or later
- Python 3.9+ (Shapely is bundled in QGIS ≥3.22)
- Works on Windows, Linux, macOS

## Usage
1. Open **Processing Toolbox** in QGIS (Ctrl+Alt+T)
2. Search for `IsoParcel` under the "Subdivision" group
3. Select input polygon layer
4. Set number of rows and columns (1-50 each)
5. Adjust optional parameters: area tolerance (m²) and max iterations per cut
6. Run. Output layer is added to the project automatically with attributes:
   - All original fields copied
   - `parent_id`: ID of source polygon
   - `parcel_idx`: Index of parcel within subdivision (1-based)

## Restrictions
- Optimized for simple polygons. Highly concave or multi-part geometries may require pre-cleaning with `v.clean` (GRASS) or similar.
- Does not preserve topological relationships between adjacent polygons (processes each feature independently).
- Tested primarily in projected CRS (UTM); geographic CRS may introduce minor area distortions due to planar approximation.
- Area equity guarantee (CV <0.01%) applies only to successful executions; failures are logged as warnings.

## License
GPL-2.0-or-later. See LICENSE file.

## Repository
Source code, issue tracker, and documentation:  
https://github.com/roger-delgado/IsoParcel

## Acknowledgements
- QGIS community for the Processing framework and PyQGIS API
- Algorithm logic refined with AI-assisted code review (2026). Final validation and scientific responsibility remain with the author.