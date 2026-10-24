/* Bounded, non-growing region storage. No user pointers escape the backend. */
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <limits.h>
#include <string.h>

typedef struct {
    size_t capacity;
    size_t used;
    max_align_t alignment;
    unsigned char data[];
} LizaRegion;

void *liza_rt_region_create(uint64_t capacity, uint32_t *error) {
    const size_t header = offsetof(LizaRegion, data);
    *error = 0;
    if (capacity > SIZE_MAX || (size_t)capacity > SIZE_MAX - header) {
        *error = 3; return NULL;
    }
    LizaRegion *region = (LizaRegion *)malloc(header + (size_t)capacity);
    if (!region) { *error = 1; return NULL; }
    region->capacity = (size_t)capacity;
    region->used = 0;
    return region;
}

void *liza_rt_region_alloc(void *handle, uint64_t element_size,
                          uint64_t alignment, uint32_t count, uint32_t *error) {
    LizaRegion *region = (LizaRegion *)handle;
    *error = 0;
    if (!alignment || alignment > _Alignof(max_align_t) ||
        (alignment & (alignment - 1)) || element_size > SIZE_MAX ||
        (count && element_size > SIZE_MAX / count)) {
        *error = 3; return NULL;
    }
    size_t bytes = (size_t)element_size * count;
    /* Empty logical values need no bytes and do not consume padding. */
    if (!bytes) return region->data;
    size_t padding = (size_t)(-(uintptr_t)region->used) & ((size_t)alignment - 1);
    if (padding > region->capacity - region->used ||
        bytes > region->capacity - region->used - padding) {
        *error = 2; return NULL;
    }
    size_t offset = region->used + padding;
    region->used = offset + bytes; /* Commit only after every check succeeded. */
    return region->data + offset;
}

void liza_rt_region_close(void *handle) { free(handle); }

/* The compiler proves origin equality and exclusive ownership of the vector.
   Length <= capacity is an invariant of its private descriptor. */
void *liza_rt_vec_reserve(void *region, void *data, uint64_t element_size,
                          uint64_t alignment, uint32_t length, uint32_t capacity,
                          uint32_t requested, uint32_t *error) {
    *error = 0;
    if (requested <= capacity) return data;
    void *next = liza_rt_region_alloc(region, element_size, alignment, requested, error);
    if (*error) return data;
    /* Success proved requested * element_size fits size_t, hence so does
       length * element_size. Old and new nonempty allocations are disjoint. */
    size_t initialized = (size_t)length * (size_t)element_size;
    if (initialized) memcpy(next, data, initialized);
    return next;
}
