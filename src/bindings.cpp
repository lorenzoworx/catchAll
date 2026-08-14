#include "catchall/audio_ring.hpp"

#include <cstddef>
#include <span>
#include <vector>

#include <nanobind/nanobind.h>
#include <nanobind/stl/vector.h>

namespace nb = nanobind;

NB_MODULE(_core, module) {
    module.doc() = "Native audio buffering for CatchAll.";

    nb::class_<catchall::AudioRing>(module, "AudioRing")
        .def(
            nb::init<std::size_t>(),
            nb::arg("capacity")
        )
        .def_prop_ro(
            "capacity",
            &catchall::AudioRing::capacity
        )
        .def_prop_ro(
            "size",
            &catchall::AudioRing::size
        )
        .def_prop_ro(
            "dropped_samples",
            &catchall::AudioRing::dropped_samples
        )
        .def(
            "write",
            [](catchall::AudioRing& ring, const std::vector<float>& samples) {
                return ring.write(
                    std::span<const float>(samples.data(),samples.size())
                );
            },
            nb::arg("samples")
        )
        .def(
            "read",
            [](catchall::AudioRing& ring, std::size_t count) -> nb::object {
                std::vector<float> output(count);

                if(!ring.read(
                    std::span<float>(output.data(), output.size())
                )) {
                    return nb::none();
                }
                
                return nb::cast(output);
            },
            nb::arg("count")
        );
}