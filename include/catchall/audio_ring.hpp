#pragma once

#include <atomic>
#include <cstddef>
#include <cstdint>
#include <span>
#include <vector>

namespace catchall {
    class AudioRing {
        public:
            explicit AudioRing(std::size_t capacity);

            AudioRing(const AudioRing&) = delete;
            AudioRing& operator=(const AudioRing&) = delete;

            [[nodiscard]] std::size_t capacity() const noexcept;
            [[nodiscard]] std::size_t size() const noexcept;
            [[nodiscard]] std::uint64_t dropped_samples() const noexcept;

            [[nodiscard]] std::size_t write(std::span<const float> samples) noexcept;
            [[nodiscard]] bool read(std::span<float> destination) noexcept;

        private:
            std::vector<float> buffer_;

            std::atomic<std::uint64_t> read_index_{0};
            std::atomic<std::uint64_t> write_index_{0};
            std::atomic<std::uint64_t> dropped_samples_{0};

    };
}
