set(MGR_DASHBOARD_V2_VIRTUALENV ${CEPH_BUILD_VIRTUALENV}/mgr-dashboard_v2-virtualenv)

add_custom_target(mgr-dashboard_v2
  COMMAND
  ${CMAKE_SOURCE_DIR}/src/tools/setup-virtualenv.sh ${MGR_DASHBOARD_V2_VIRTUALENV} &&
  ${MGR_DASHBOARD_V2_VIRTUALENV}/bin/pip install --no-index --use-wheel --find-links=file:${CMAKE_SOURCE_DIR}/src/pybind/mgr/dashboard_v2/wheelhouse -r requirements.txt
  WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}/src/pybind/mgr/dashboard_v2
  COMMENT "mgr-dashboard_v2 is being created")
add_dependencies(tests mgr-dashboard_v2)

include(Distutils)
distutils_install_module(mgr_dashboard_v2)

option(WITH_MGR_DASHBOARD_V2_FRONTEND "Build the mgr/dashboard_v2 frontend using `npm`" ON)
if(WITH_MGR_DASHBOARD_V2_FRONTEND)

# Glob some frontend files. With CMake 3.6, this can be simplified
# to *.ts *.html. Just add:
# list(FILTER frontend_src INCLUDE REGEX "frontend/src")
file(
  GLOB_RECURSE frontend_src
  frontend/src/*.ts
  frontend/src/*.html
  frontend/src/*/*.ts
  frontend/src/*/*.html
  frontend/src/*/*/*.ts
  frontend/src/*/*/*.html
  frontend/src/*/*/*/*.ts
  frontend/src/*/*/*/*.html
  frontend/src/*/*/*/*/*.ts
  frontend/src/*/*/*/*/*.html
  frontend/src/*/*/*/*/*/*.ts
  frontend/src/*/*/*/*/*/*.html)

if(NOT CMAKE_BUILD_TYPE STREQUAL Debug)
  set(npm_command npm install && npm build -- --prod)
else()
  set(npm_command npm install && npm build)
endif()

add_custom_command(
  OUTPUT "${CMAKE_SOURCE_DIR}/src/pybind/mgr/dashboard_v2/frontend/dist/index.html"
  COMMAND ${npm_command}
  DEPENDS ${frontend_src}
  WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}/src/pybind/mgr/dashboard_v2/frontend
  COMMENT "mgr-dashboard_v2-frontend is being created"
)
add_custom_target(mgr-dashboard_v2-frontend
  DEPENDS frontend/dist/index.html
  WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}/src/pybind/mgr/dashboard_v2/frontend
)
add_dependencies(ceph-mgr mgr-dashboard_v2-frontend)
endif(WITH_MGR_DASHBOARD_V2_FRONTEND)
