// Minimal stub Vulkan null driver header to satisfy tcuNullPlatform without real Vulkan
#ifndef _VKNULLDRIVER_STUB_HPP
#define _VKNULLDRIVER_STUB_HPP

#include "vkPlatform.hpp"

namespace vk {

class NullDriver : public Library {
public:
    virtual ~NullDriver() {}
};

inline Library* createNullDriver() {
    // Return a trivial Library instance; callers may delete it.
    return new NullDriver();
}

} // namespace vk

#endif // _VKNULLDRIVER_STUB_HPP
