/* Platform policy verification, called synchronously inside the TLS handshake.
 * No network fetching, no modification of system trust stores. */
#if defined(__APPLE__)
#include <Security/Security.h>
#include <CoreFoundation/CoreFoundation.h>
static int liza_tls_os_chain(X509_STORE_CTX *store,const char *peer,X509_STORE *anchors) {
    CFMutableArrayRef certs=CFArrayCreateMutable(NULL,0,&kCFTypeArrayCallBacks);
    CFStringRef host=CFStringCreateWithCString(NULL,peer,kCFStringEncodingASCII);
    SecPolicyRef policy=host?SecPolicyCreateSSL(true,host):NULL;
    SecTrustRef trust=NULL;CFMutableArrayRef roots=NULL;int ok=0;
    STACK_OF(X509) *chain=X509_STORE_CTX_get0_untrusted(store);
    X509 *leaf=X509_STORE_CTX_get0_cert(store);
    if(!certs||!policy||!leaf)goto done;
    unsigned total=0;
    for(int i=-1;i<(chain?sk_X509_num(chain):0);i++){
        X509 *cert=i<0?leaf:sk_X509_value(chain,i);
        if(i>=0&&cert==leaf)continue;
        int n=i2d_X509(cert,NULL);if(n<=0||n>65536||total+(unsigned)n>65536)goto done;
        total+=(unsigned)n;unsigned char *der=OPENSSL_malloc((size_t)n),*p=der;
        if(!der)goto done;
        int encoded=i2d_X509(cert,&p);
        CFDataRef bytes=encoded==n?CFDataCreate(NULL,der,n):NULL;OPENSSL_free(der);
        SecCertificateRef c=bytes?SecCertificateCreateWithData(NULL,bytes):NULL;
        if(bytes)CFRelease(bytes);
        if(!c)goto done;
        CFArrayAppendValue(certs,c);CFRelease(c);
        if(CFArrayGetCount(certs)>9)goto done;
    }
    if(SecTrustCreateWithCertificates(certs,policy,&trust)!=errSecSuccess)goto done;
    if(anchors){
        roots=CFArrayCreateMutable(NULL,0,&kCFTypeArrayCallBacks);if(!roots)goto done;
        const STACK_OF(X509_OBJECT) *objects=X509_STORE_get0_objects(anchors);
        unsigned root_bytes=0;
        for(int i=0;i<sk_X509_OBJECT_num(objects);i++){
            X509 *cert=X509_OBJECT_get0_X509(sk_X509_OBJECT_value(objects,i));if(!cert)continue;
            int n=i2d_X509(cert,NULL);if(n<=0||n>65536||root_bytes+(unsigned)n>2097152||CFArrayGetCount(roots)>=256)goto done;
            root_bytes+=(unsigned)n;unsigned char *der=OPENSSL_malloc((size_t)n),*p=der;if(!der)goto done;
            int encoded=i2d_X509(cert,&p);CFDataRef bytes=encoded==n?CFDataCreate(NULL,der,n):NULL;OPENSSL_free(der);
            SecCertificateRef c=bytes?SecCertificateCreateWithData(NULL,bytes):NULL;if(bytes)CFRelease(bytes);
            if(!c)goto done;CFArrayAppendValue(roots,c);CFRelease(c);
        }
        if(!CFArrayGetCount(roots)||SecTrustSetAnchorCertificates(trust,roots)!=errSecSuccess||SecTrustSetAnchorCertificatesOnly(trust,true)!=errSecSuccess)goto done;
    }
    if(SecTrustSetNetworkFetchAllowed(trust,false)!=errSecSuccess)goto done;
    ok=SecTrustEvaluateWithError(trust,NULL)?1:0;
done:
    if(trust)CFRelease(trust);
    if(roots)CFRelease(roots);
    if(policy)CFRelease(policy);
    if(host)CFRelease(host);
    if(certs)CFRelease(certs);
    return ok;
}
#elif defined(_WIN32)
#include <wincrypt.h>
static int liza_tls_os_chain(X509_STORE_CTX *store,const char *peer,X509_STORE *anchors) {
    HCERTSTORE certs=CertOpenStore(CERT_STORE_PROV_MEMORY,0,0,CERT_STORE_CREATE_NEW_FLAG,NULL);
    HCERTSTORE roots=NULL;HCERTCHAINENGINE engine=NULL;
    PCCERT_CONTEXT leaf=NULL;PCCERT_CHAIN_CONTEXT chain=NULL;int ok=0;
    WCHAR host[254];int host_n=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,peer,-1,host,254);
    STACK_OF(X509) *provided=X509_STORE_CTX_get0_untrusted(store);
    X509 *first=X509_STORE_CTX_get0_cert(store);
    if(!certs||!host_n||!first)goto done;
    unsigned total=0,count=0;
    for(int i=-1;i<(provided?sk_X509_num(provided):0);i++){
        X509 *cert=i<0?first:sk_X509_value(provided,i);
        if(i>=0&&cert==first)continue;
        int n=i2d_X509(cert,NULL);if(n<=0||n>65536||total+(unsigned)n>65536||++count>9)goto done;
        total+=(unsigned)n;unsigned char *der=OPENSSL_malloc((size_t)n),*p=der;
        if(!der)goto done;
        int encoded=i2d_X509(cert,&p);
        PCCERT_CONTEXT c=encoded==n?CertCreateCertificateContext(X509_ASN_ENCODING,der,(DWORD)n):NULL;
        OPENSSL_free(der);if(!c)goto done;
        if(i<0)leaf=c;
        BOOL added=CertAddCertificateContextToStore(certs,c,CERT_STORE_ADD_ALWAYS,NULL);
        if(i>=0)CertFreeCertificateContext(c);
        if(!added)goto done;
    }
    if(anchors){
        roots=CertOpenStore(CERT_STORE_PROV_MEMORY,0,0,CERT_STORE_CREATE_NEW_FLAG,NULL);if(!roots)goto done;
        const STACK_OF(X509_OBJECT) *objects=X509_STORE_get0_objects(anchors);unsigned root_bytes=0,root_count=0;
        for(int i=0;i<sk_X509_OBJECT_num(objects);i++){
            X509 *cert=X509_OBJECT_get0_X509(sk_X509_OBJECT_value(objects,i));if(!cert)continue;
            int n=i2d_X509(cert,NULL);if(n<=0||n>65536||root_bytes+(unsigned)n>2097152||++root_count>256)goto done;
            root_bytes+=(unsigned)n;unsigned char *der=OPENSSL_malloc((size_t)n),*p=der;if(!der)goto done;
            int encoded=i2d_X509(cert,&p);PCCERT_CONTEXT c=encoded==n?CertCreateCertificateContext(X509_ASN_ENCODING,der,(DWORD)n):NULL;
            OPENSSL_free(der);if(!c)goto done;
            BOOL added=CertAddCertificateContextToStore(roots,c,CERT_STORE_ADD_ALWAYS,NULL);CertFreeCertificateContext(c);if(!added)goto done;
        }
        if(!root_count)goto done;
        CERT_CHAIN_ENGINE_CONFIG config;memset(&config,0,sizeof(config));config.cbSize=sizeof(config);config.hExclusiveRoot=roots;
        if(!CertCreateCertificateChainEngine(&config,&engine))goto done;
    }
    {
        LPSTR usage=szOID_PKIX_KP_SERVER_AUTH;
        CERT_CHAIN_PARA params;memset(&params,0,sizeof(params));params.cbSize=sizeof(params);
        params.RequestedUsage.dwType=USAGE_MATCH_TYPE_AND;
        params.RequestedUsage.Usage.cUsageIdentifier=1;params.RequestedUsage.Usage.rgpszUsageIdentifier=&usage;
        DWORD flags=CERT_CHAIN_CACHE_ONLY_URL_RETRIEVAL|CERT_CHAIN_DISABLE_AUTH_ROOT_AUTO_UPDATE;
        if(!CertGetCertificateChain(engine,leaf,NULL,certs,&params,flags,NULL,&chain))goto done;
        SSL_EXTRA_CERT_CHAIN_POLICY_PARA ssl;memset(&ssl,0,sizeof(ssl));ssl.cbSize=sizeof(ssl);
        ssl.dwAuthType=AUTHTYPE_SERVER;ssl.pwszServerName=host;
        CERT_CHAIN_POLICY_PARA policy;memset(&policy,0,sizeof(policy));policy.cbSize=sizeof(policy);policy.pvExtraPolicyPara=&ssl;
        CERT_CHAIN_POLICY_STATUS status;memset(&status,0,sizeof(status));status.cbSize=sizeof(status);
        ok=CertVerifyCertificateChainPolicy(CERT_CHAIN_POLICY_SSL,chain,&policy,&status)&&!status.dwError;
    }
done:
    if(chain)CertFreeCertificateChain(chain);
    if(leaf)CertFreeCertificateContext(leaf);
    if(certs)CertCloseStore(certs,0);
    if(engine)CertFreeCertificateChainEngine(engine);
    if(roots)CertCloseStore(roots,0);
    return ok;
}
#endif
