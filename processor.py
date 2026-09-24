# -*- coding: utf-8 -*-
"""
processor.py
Модуль с бизнес-логикой обработки слоёв для плагина cl_r.
Здесь собрана логика, ранее находившаяся в методе run():
  - загрузка административного слоя,
  - выбор объекта по атрибуту,
  - цикл по входным слоям: обрезка – перепроецирование – сохранение.
"""

import os.path
import glob

from qgis.core import (
    QgsMessageLog,
    QgsVectorLayer,
    QgsProcessingFeatureSourceDefinition,
    QgsProject,
)
from qgis import processing


LOG_TAG = 'MyPlugin'
TARGET_CRS = 'EPSG:32644'


def load_admin_layer(adm_shp, layer_name="nso", add_to_project=True):
    """Загрузка административного слоя.

    :param adm_shp: путь к shape-файлу административного слоя
    :param layer_name: имя слоя
    :param add_to_project: добавлять ли слой в проект
    :returns: загруженный QgsVectorLayer
    """
    QgsMessageLog.logMessage(adm_shp, LOG_TAG)
    layer = QgsVectorLayer(adm_shp, layer_name, "ogr")
    if add_to_project:
        QgsProject.instance().addMapLayer(layer)
    return layer


def select_feature_by_attribute(layer, attribute, value):
    """Выбор объекта по атрибуту.

    :param layer: слой, в котором выполняется выбор
    :param attribute: имя атрибута
    :param value: значение атрибута
    """
    expression = '"{attr}"=\'{val}\''.format(attr=attribute, val=value)
    QgsMessageLog.logMessage("Selecting by: " + expression, LOG_TAG)
    layer.selectByExpression(expression, QgsVectorLayer.SetSelection)


def process_layers(osm_dir, result_dir, overlay_layer, target_crs=TARGET_CRS):
    """Цикл по входным слоям: обрезка – перепроецирование – сохранение.

    :param osm_dir: каталог с исходными shape-файлами
    :param result_dir: каталог для сохранения результатов
    :param overlay_layer: слой обрезки (административный, с выбранным объектом)
    :param target_crs: целевая система координат для перепроецирования
    """
    for shp_file in glob.glob(os.path.join(osm_dir, "*.shp")):
        base_name = os.path.basename(shp_file)
        clip_path = os.path.join(result_dir, base_name)

        QgsMessageLog.logMessage(shp_file, LOG_TAG)
        processing.run('qgis:clip', {
            "INPUT": shp_file,
            "OVERLAY": QgsProcessingFeatureSourceDefinition(
                overlay_layer.id(), selectedFeaturesOnly=True),
            "OUTPUT": clip_path,
        })

        QgsMessageLog.logMessage("Reprojecting:" + shp_file, LOG_TAG)
        proj_name = os.path.splitext(base_name)[0] + "_proj.shp"
        proj_path = os.path.join(result_dir, proj_name)
        processing.run('qgis:reprojectlayer', {
            "INPUT": clip_path,
            "TARGET_CRS": target_crs,
            "OUTPUT": proj_path,
        })


def run_processing(osm_dir, adm_shp, result_dir,
                   filter_attribute, filter_value):
    """Полный сценарий обработки — оркестрация всех шагов.

    :param osm_dir: каталог с исходными shape-файлами
    :param adm_shp: путь к административному слою
    :param result_dir: каталог для результатов
    :param filter_attribute: имя атрибута для выбора объекта
    :param filter_value: значение атрибута для выбора объекта
    """
    QgsMessageLog.logMessage(osm_dir, LOG_TAG)

    # 1. Загрузка административного слоя
    layer = load_admin_layer(adm_shp)

    # 2. Выбор объекта по атрибуту
    select_feature_by_attribute(layer, filter_attribute, filter_value)

    # 3. Обработка слоёв
    process_layers(osm_dir, result_dir, layer)