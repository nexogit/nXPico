add_library(usermod_nrf9151 INTERFACE)

target_sources(usermod_nrf9151 INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/nrf9151.c
)

target_include_directories(usermod_nrf9151 INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_nrf9151)

add_library(usermod_x509gen INTERFACE)

target_sources(usermod_x509gen INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/mod_x509gen.c
)

target_include_directories(usermod_x509gen INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_x509gen)
