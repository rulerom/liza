/* Copyright (c) 2026 Anton Golovkov udattsk@gmail.com
 * SPDX-License-Identifier: BSL-1.0 */
#include <stdint.h>
#include <string.h>
#include <openssl/hmac.h>
#include <openssl/crypto.h>

uint32_t liza_rt_hmac_sha256(const uint8_t *key,uint32_t kn,
                            const uint8_t *data,uint32_t dn,uint8_t *out) {
    if (!out) return 1;
    memset(out,0,32);
    if (!key || !kn || kn>1024 || dn>4096 || (!data && dn)) return 1;
    unsigned int size=0;
    if (!HMAC(EVP_sha256(),key,(int)kn,data,dn,out,&size) || size!=32) {
        OPENSSL_cleanse(out,32);return 2;
    }
    return 0;
}
