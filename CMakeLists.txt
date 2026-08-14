cmake_minimum_required(VERSION 3.26)

project(catchall LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(
    CATCHALL_ENABLE_TSAN
    "Enable ThreadSanitizer for native tests"
    OFF
)

add_library(catchall_audio STATIC
    src/audio_ring.cpp
)

set_target_properties(
    catchall_audio
    PROPERTIES
        POSITION_INDEPENDENT_CODE ON
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

if(SKBUILD)
    find_package(
        Python 3.12
        REQUIRED COMPONENTS
            Interpreter
            Development.Module
    )

    find_package(nanobind CONFIG REQUIRED)

    nanobind_add_module(
        _core
        NB_STATIC
        src/bindings.cpp
    )

    target_link_libraries(
        _core
        PRIVATE
            catchall_audio
    )

    install(
        TARGETS _core
        LIBRARY DESTINATION catchall
    )
endif()

include(CTest)

if(BUILD_TESTING)
    find_package(Threads REQUIRED)

    add_executable(audio_ring_tests
        tests/test_audio_ring.cpp
    )

    target_link_libraries(audio_ring_tests
        PRIVATE
            catchall_audio
            Threads::Threads
    )

    add_test(
        NAME audio_ring
        COMMAND audio_ring_tests
    )

    if(CATCHALL_ENABLE_TSAN)
        if(MSVC)
            message(FATAL_ERROR "ThreadSanitizer is not configured for MSVC")
        endif()

        target_compile_options(
            catchall_audio
            PRIVATE
                -fsanitize=thread
                -fno-omit-frame-pointer
        )

        target_compile_options(
            audio_ring_tests
            PRIVATE
                -fsanitize=thread
                -fno-omit-frame-pointer
        )

        target_link_options(
            audio_ring_tests
            PRIVATE
                -fsanitize=thread
        )
    endif()
endif()