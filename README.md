# IsoParcel

Equitable polygon subdivision into configurable row*column grids with automatic topological cleaning.

## Description
IsoParcel partitions input polygon layers into equal-area parcels using an adaptive orthogonal cutting algorithm with binary search convergence. Invalid geometries are repaired before cutting, and successful subdivisions reach an area coefficient of variation (CV) below 0.01% for cadastral, agricultural, and experimental design workflows.

**Concept initiated**: 2026-05-15

## Tutorial
Step-by-step guide with figures: [English](docs/TUTORIAL.md) · [Español](docs/TUTORIAL_es.md)

## Features
- Subdivides polygons into N×M parcels with mathematically controlled area equity
- Automatic repair of self-intersections and degenerate vertices (`makeValid` + `buffer(0)`)
- MultiPolygon inputs: the largest part is subdivided and a warning reports the parts left out
- Warning when a feature produces fewer parcels than requested, so it can be reviewed
- Integrated into QGIS Processing Toolbox (supports batch processing and graphical models)
- Configurable tolerance and iteration limits for precision control

## Requirements
- QGIS 3.34 or later (it uses the Python interpreter and Shapely bundled with QGIS)
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
- Optimized for simple polygons. Highly concave or multi-part geometries may require pre-cleaning with `v.clean` (GRASS) or similar, or splitting with *Multipart to singleparts*.
- Does not preserve topological relationships between adjacent polygons (processes each feature independently).
- Use a projected CRS with units in metres (e.g. UTM): the area tolerance is given in m², so layers in geographic coordinates should be reprojected first.
- Area equity (CV <0.01%) applies only to successful executions; failures are logged as warnings.

## Changelog
 - **1.0.3** (2026-11-13): fixed the cut position of the binary search (the converged position is now used instead of the last upper bound), so parcel areas are more equal and more subdivisions meet the 0.01% criterion.
 - **1.0.2** (2026-11-11): fixed the orientation angle (the closing vertex of the ring is no longer used to find the base segment); warnings for multipart features and for fewer parcels than requested.
 - **1.0.1** (2026-05-15): added CITATION.cff and corrected the DOI format.
 - **1.0.0** (2026-05-15): initial release.

## How to cite
Delgado-Alcívar, R. A. (2026). IsoParcel: Equal-area polygon partitioning plugin for QGIS [Computer software]. Zenodo. https://doi.org/10.5281/zenodo.20225169

This DOI always resolves to the latest version. Each version has its own DOI, listed on the Zenodo record.

## License
GPL-2.0-or-later. See LICENSE file.

## Repository
Source code, issue tracker, and documentation:  
https://github.com/roger-delgado/IsoParcel

## Acknowledgements
- QGIS community for the Processing framework and PyQGIS API
- The validation benchmarks were run on the high-performance computing infrastructure of CEDIA (Corporación Ecuatoriana para el Desarrollo de la Investigación y la Academia)
- Algorithm logic refined with AI-assisted code review (2026). Final validation and scientific responsibility remain with the author.
