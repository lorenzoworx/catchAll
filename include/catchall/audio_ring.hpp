#pragma once

#include <cstddef>
#include <cstdint>
#include <span>
#include <vector>

namespace catchall {
    class AudioRing {
        public:
            explicit AudioRing(std::size_t capacity);

            [[nodiscard]] std::size_t capacity() const noexcept;
            [[nodiscard]] std::size_t size() const noexcept;
            [[nodiscard]] std::uint64_t dropped_samples() const noexcept;

            void write(std::span<const float> samples);
            [[nodiscard]] bool read(std::span<float> destination);

        private:
            std::vector<float> buffer_;
            std::size_t read_position_{0};
            std::size_t write_position_{0};
            std::size_t size_{0};
            std::uint64_t dropped_samples_{0};    

    };
}
