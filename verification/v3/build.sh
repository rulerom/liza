#!/bin/sh
# Explicit opt-in dependency build; not part of normal Liza compilation.
set -eu
: "${ALIVE_SOURCE:?Set ALIVE_SOURCE to an Alive2 checkout}"
: "${LLVM_PREFIX:?Set LLVM_PREFIX to a compatible LLVM installation}"
: "${Z3_PREFIX:?Set Z3_PREFIX to a Z3 installation}"
if [ -f "$Z3_PREFIX/lib/libz3.dylib" ]; then
    Z3_LIBRARY="$Z3_PREFIX/lib/libz3.dylib"
else
    Z3_LIBRARY="$Z3_PREFIX/lib/libz3.so"
fi
REVISION=a68009c9e81575bdcc249d3cc534514a76112221
actual=$(git -C "$ALIVE_SOURCE" rev-parse HEAD)
if [ "$actual" != "$REVISION" ] || [ -n "$(git -C "$ALIVE_SOURCE" status --porcelain)" ]; then
    echo 'Expected clean pinned Alive2 checkout' >&2
    exit 1
fi
cmake -S "$ALIVE_SOURCE" -B "$ALIVE_SOURCE/build" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DBUILD_TV=ON \
    -DLLVM_DIR="$LLVM_PREFIX/lib/cmake/llvm" \
    -DZ3_INCLUDE_DIR="$Z3_PREFIX/include" \
    -DZ3_LIBRARIES="$Z3_LIBRARY"
cmake --build "$ALIVE_SOURCE/build" --target alive-tv -j 4
