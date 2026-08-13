cmake_minimum_required(VERSION 3.26)

project(catchall LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(catchall_audio STATIC
    src/audio_ring.cpp
)

target_include_directories(catchall_audio
    PUBLIC
        include
)

if(MSVC)
    target_compile_options(catchall_audio PRIVATE /W4)
else()
    target_compile_options(catchall_audio PRIVATE -Wall -Wextra -Wpedantic)
endif()

include(CTest)

if(BUILD_TESTING)
    add_executable(audio_ring_tests
        tests/test_audio_ring.cpp
    )

    target_link_libraries(audio_ring_tests
        PRIVATE
            catchall_audio
    )

    add_test(
        NAME audio_ring
        COMMAND audio_ring_tests
    )
endif()