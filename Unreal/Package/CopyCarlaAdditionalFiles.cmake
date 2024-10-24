message("${CARLA_SOURCE_DIR} ${CARLA_TARGET_PACKAGE_PATH} ${CARLA_BINARY_DIR}")
file(COPY_FILE ${CARLA_SOURCE_DIR}/LICENSE ${CARLA_TARGET_PACKAGE_PATH}/LICENSE)
file(COPY_FILE ${CARLA_SOURCE_DIR}/CHANGELOG.md ${CARLA_TARGET_PACKAGE_PATH}/CHANGELOG)
file(COPY ${CARLA_SOURCE_DIR}/dtc_manager DESTINATION ${CARLA_TARGET_PACKAGE_PATH})

make_directory(${CARLA_TARGET_PACKAGE_PATH}/PythonAPI/carla/dist)
file(GLOB PYTHON_WHL_FILES ${CARLA_BINARY_DIR}/PythonAPI/dist/carla-*.whl)
file(COPY ${PYTHON_WHL_FILES} DESTINATION ${CARLA_TARGET_PACKAGE_PATH}/PythonAPI/carla/dist/)
file(COPY ${CARLA_SOURCE_DIR}/PythonAPI/carla/agents/ DESTINATION ${CARLA_TARGET_PACKAGE_PATH}/PythonAPI/carla/agents/)
file(COPY_FILE ${CARLA_SOURCE_DIR}/PythonAPI/carla/scene_layout.py ${CARLA_TARGET_PACKAGE_PATH}/PythonAPI/carla/scene_layout.py)
file(COPY_FILE ${CARLA_SOURCE_DIR}/PythonAPI/carla/requirements.txt ${CARLA_TARGET_PACKAGE_PATH}/PythonAPI/carla/requirements.txt)

make_directory(${CARLA_TARGET_PACKAGE_PATH}/PythonAPI/examples/)
file(GLOB PYTHON_EXAMPLE_FILES ${CARLA_SOURCE_DIR}/PythonAPI/examples/*.py)
file(COPY ${PYTHON_EXAMPLE_FILES} DESTINATION ${CARLA_TARGET_PACKAGE_PATH}/PythonAPI/examples/)
make_directory(${CARLA_TARGET_PACKAGE_PATH}/PythonAPI/examples/rss/)
file(GLOB PYTHON_EXAMPLE_RSS_FILES ${CARLA_SOURCE_DIR}/PythonAPI/examples/rss/*.py)
file(COPY ${PYTHON_EXAMPLE_RSS_FILES} DESTINATION ${CARLA_TARGET_PACKAGE_PATH}/PythonAPI/examples/rss/)

make_directory(${CARLA_TARGET_PACKAGE_PATH}/PythonAPI/util/)
file(GLOB PYTHON_UTIL_FILES ${CARLA_SOURCE_DIR}/PythonAPI/util/*.py)
file(COPY ${PYTHON_UTIL_FILES} DESTINATION ${CARLA_TARGET_PACKAGE_PATH}/PythonAPI/util/)
file(COPY_FILE ${CARLA_SOURCE_DIR}/PythonAPI/util/requirements.txt ${CARLA_TARGET_PACKAGE_PATH}/PythonAPI/util/requirements.txt)
file(COPY ${CARLA_SOURCE_DIR}/PythonAPI/util/opendrive/ DESTINATION ${CARLA_TARGET_PACKAGE_PATH}/PythonAPI/util/opendrive/)
