// Minimal stub Vulkan platform header (project root)
#ifndef _VKPLATFORM_STUB_HPP
#define _VKPLATFORM_STUB_HPP

namespace vk {

class Library { public: virtual ~Library() {} };

class Platform {
public:
    enum LibraryType { LIBRARY_TYPE_VULKAN = 0, LIBRARY_TYPE_VULKAN_SC = 1 };
    virtual ~Platform() {}
    virtual Library* createLibrary(LibraryType, const char* path = nullptr) const = 0;
};

} // namespace vk

#endif // _VKPLATFORM_STUB_HPP
// Minimal stub Vulkan platform header to satisfy null platform without real Vulkan dependency.
#ifndef _VKPLATFORM_STUB_HPP
#define _VKPLATFORM_STUB_HPP

namespace vk {

class Library { public: virtual ~Library() {} };

class Platform {
public:
    enum LibraryType { LIBRARY_TYPE_VULKAN = 0, LIBRARY_TYPE_VULKAN_SC = 1 };
    virtual ~Platform() {}
    virtual Library* createLibrary(LibraryType, const char* path = nullptr) const = 0;
};

} // namespace vk

#endif // _VKPLATFORM_STUB_HPP
