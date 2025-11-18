// Minimal Vulkan platform & driver stubs to satisfy VK-GL-CTS surfaceless platform build
// These do NOT provide real Vulkan functionality; they only supply the types & signatures
// referenced by tcuSurfacelessPlatform.cpp. If full Vulkan tests are required, replace this
// file with the original vkPlatform.hpp / vk headers from upstream VK-GL-CTS.

#ifndef VK_PLATFORM_MINI_STUB_HPP
#define VK_PLATFORM_MINI_STUB_HPP

namespace tcu {
class DynamicFunctionLibrary; // forward declaration (real implementation in upstream)
class FunctionLibrary;        // forward declaration
}

namespace vk {

class PlatformInterface {
public:
    virtual ~PlatformInterface() {}
};

class Library {
public:
    virtual ~Library() {}
    // Optional helper for surfaceless platform: default empty platform interface
    virtual const PlatformInterface& getPlatformInterface() const { return *m_dummyInterface; }
    // Function library accessor expected by surfaceless code; returns nullptr in stub.
    virtual const tcu::FunctionLibrary& getFunctionLibrary() const { return *reinterpret_cast<const tcu::FunctionLibrary*>(m_dummyInterface); }
protected:
    // We use a static dummy interface object to avoid allocating.
    static const PlatformInterface* m_dummyInterface;
};

// Simple driver that acts as a PlatformInterface wrapper.
class PlatformDriver : public PlatformInterface {
public:
    explicit PlatformDriver(const tcu::DynamicFunctionLibrary&) {}
    virtual ~PlatformDriver() {}
};

class Platform {
public:
    enum LibraryType { LIBRARY_TYPE_VULKAN = 0, LIBRARY_TYPE_VULKAN_SC = 1 };
    virtual ~Platform() {}
    // Provide a non-pure default so downstream platform subclasses that only override
    // createLibrary(const char*) are still concrete.
    // virtual Library* createLibrary(LibraryType, const char* path = nullptr) const { (void)path; return nullptr; }
};

} // namespace vk

#endif // VK_PLATFORM_MINI_STUB_HPP
