/*
 * mbedtls_config_x509gen.h
 *
 * Override per abilitare le funzionalità x509write in mbedTLS.
 *
 * Questo file va incluso DOPO la config mbedTLS di default di MicroPython.
 * Vedi il README per come applicarlo nella build.
 *
 * In alternativa, puoi modificare direttamente il file:
 *   ports/rp2/mbedtls/mbedtls_config.h
 * aggiungendo i #define qui sotto.
 */

#ifndef MBEDTLS_CONFIG_X509GEN_H
#define MBEDTLS_CONFIG_X509GEN_H

/* ─── Inclusione config base MicroPython ─── */
/* Questa riga va commentata se modifichi direttamente mbedtls_config.h */
// #include "ports/rp2/mbedtls/mbedtls_config.h"

/* ═══════════════════════════════════════════════
 * Feature OBBLIGATORIE per x509gen
 *
 * Se una di queste è già definita nella config
 * base, il #ifndef evita ridefinizioni.
 * ═══════════════════════════════════════════════ */

/* Scrittura certificati X.509 */
#ifndef MBEDTLS_X509_CRT_WRITE_C
#define MBEDTLS_X509_CRT_WRITE_C
#endif

/* Scrittura CSR */
#ifndef MBEDTLS_X509_CSR_WRITE_C
#define MBEDTLS_X509_CSR_WRITE_C
#endif

/* Creazione certificati (include x509write_crt.h) */
#ifndef MBEDTLS_X509_CREATE_C
#define MBEDTLS_X509_CREATE_C
#endif

/* Parsing chiavi (necessario per pk_parse_key) */
#ifndef MBEDTLS_PK_PARSE_C
#define MBEDTLS_PK_PARSE_C
#endif

/* Scrittura chiavi in PEM */
#ifndef MBEDTLS_PK_WRITE_C
#define MBEDTLS_PK_WRITE_C
#endif

/* Supporto formato PEM (encode/decode) */
#ifndef MBEDTLS_PEM_WRITE_C
#define MBEDTLS_PEM_WRITE_C
#endif

#ifndef MBEDTLS_PEM_PARSE_C
#define MBEDTLS_PEM_PARSE_C
#endif

/* Base64 (necessario per PEM) */
#ifndef MBEDTLS_BASE64_C
#define MBEDTLS_BASE64_C
#endif

/* OID management */
#ifndef MBEDTLS_OID_C
#define MBEDTLS_OID_C
#endif

/* ASN.1 write (necessario per x509write) */
#ifndef MBEDTLS_ASN1_WRITE_C
#define MBEDTLS_ASN1_WRITE_C
#endif

#ifndef MBEDTLS_ASN1_PARSE_C
#define MBEDTLS_ASN1_PARSE_C
#endif

/* Big numbers (per serial number e RSA) */
#ifndef MBEDTLS_BIGNUM_C
#define MBEDTLS_BIGNUM_C
#endif

/* ═══════════════════════════════════════════════
 * Algoritmi crittografici
 * ═══════════════════════════════════════════════ */

/* RSA */
#ifndef MBEDTLS_RSA_C
#define MBEDTLS_RSA_C
#endif

#ifndef MBEDTLS_GENPRIME
#define MBEDTLS_GENPRIME
#endif

/* EC (Elliptic Curve) */
#ifndef MBEDTLS_ECP_C
#define MBEDTLS_ECP_C
#endif

#ifndef MBEDTLS_ECDSA_C
#define MBEDTLS_ECDSA_C
#endif

/* Curve specifiche */
#ifndef MBEDTLS_ECP_DP_SECP256R1_ENABLED
#define MBEDTLS_ECP_DP_SECP256R1_ENABLED
#endif

#ifndef MBEDTLS_ECP_DP_SECP384R1_ENABLED
#define MBEDTLS_ECP_DP_SECP384R1_ENABLED
#endif

/* Hash */
#ifndef MBEDTLS_SHA256_C
#define MBEDTLS_SHA256_C
#endif

#ifndef MBEDTLS_SHA384_C
#define MBEDTLS_SHA384_C
#endif

#ifndef MBEDTLS_SHA512_C
#define MBEDTLS_SHA512_C
#endif

#ifndef MBEDTLS_MD_C
#define MBEDTLS_MD_C
#endif

/* Entropy e DRBG */
#ifndef MBEDTLS_ENTROPY_C
#define MBEDTLS_ENTROPY_C
#endif

#ifndef MBEDTLS_CTR_DRBG_C
#define MBEDTLS_CTR_DRBG_C
#endif

/* Errori testuali (utile per debug, può essere rimosso per risparmiare flash) */
#ifndef MBEDTLS_ERROR_C
#define MBEDTLS_ERROR_C
#endif

#endif /* MBEDTLS_CONFIG_X509GEN_H */
