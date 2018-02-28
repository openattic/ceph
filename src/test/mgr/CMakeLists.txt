#scripts
add_ceph_test(mgr-dashboard-smoke.sh ${CMAKE_CURRENT_SOURCE_DIR}/mgr-dashboard-smoke.sh)

add_ceph_test(mgr-dashboard_v2-frontend-unittests ${CMAKE_SOURCE_DIR}/src/pybind/mgr/dashboard_v2/run-frontend-unittests.sh)
