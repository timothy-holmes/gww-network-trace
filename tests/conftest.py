"""
This class contains fixtures and common helper function to keep the test files
shorter.

pytest-qgis (https://pypi.org/project/pytest-qgis) contains the following helpful
fixtures:

* qgis_app initializes and returns fully configured QgsApplication.
  This fixture is called automatically on the start of pytest session.
* qgis_canvas initializes and returns QgsMapCanvas
* qgis_iface returns mocked QgsInterface
* new_project makes sure that all the map layers and configurations are removed.
  This should be used with tests that add stuff to QgsProject.

"""

import pytest
from pytest_qgis import qgis_load_layer, qgis_project


@pytest.fixture(scope="session")
def project_with_pipes(qgis_app: QgsApplication, qgis_iface: QgsInterface):
    return None
