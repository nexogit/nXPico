/*
 * mod_x509gen.c — MicroPython C user module to generate X.509 certificates and CSRs using mbedTLS
 *
 *
 */

#include <string.h>
#include <stdio.h>

/* MicroPython headers */
#include "py/runtime.h"
#include "py/obj.h"
#include "py/objstr.h"
#include "py/mphal.h"

/* mbedTLS headers */
#include "mbedtls/pk.h"
#include "mbedtls/rsa.h"
#include "mbedtls/ecp.h"
#include "mbedtls/entropy.h"
#include "mbedtls/ctr_drbg.h"
#include "mbedtls/x509_crt.h"
#include "mbedtls/x509_csr.h"
#include "mbedtls/error.h"
#include "mbedtls/md.h"
#include "mbedtls/bignum.h"
#include "mbedtls/pem.h"
#include "mbedtls/pk.h"

/* definition of static  */
#ifndef STATIC
#define STATIC static
#endif


/* Buffer PEM */
#define PEM_BUF_SIZE  4096

/* Personalization string per il DRBG */
static const char *DRBG_PERS = "micropython_x509gen";

/* Helper: raise exception with mbedtls error message */
static void raise_mbedtls_error(int ret, const char *context) {
    char errbuf[128];
    mbedtls_strerror(ret, errbuf, sizeof(errbuf));

    mp_raise_msg_varg(&mp_type_OSError,
        MP_ERROR_TEXT("%s failed: -0x%04X %s"),
        context, (unsigned int)-ret, errbuf);
}

/* Helper: initialize entropy and DRBG */
static int init_rng(mbedtls_entropy_context *entropy,
                    mbedtls_ctr_drbg_context *drbg) {
    mbedtls_entropy_init(entropy);
    mbedtls_ctr_drbg_init(drbg);

    int ret = mbedtls_ctr_drbg_seed(drbg, mbedtls_entropy_func, entropy,
                                     (const unsigned char *)DRBG_PERS,
                                     strlen(DRBG_PERS));
    return ret;
}

// Helper: free entropy and DRBG contexts
static void cleanup_rng(mbedtls_entropy_context *entropy,
                        mbedtls_ctr_drbg_context *drbg) {
    mbedtls_ctr_drbg_free(drbg);
    mbedtls_entropy_free(entropy);
}

/* Helper: export private key in PEM format */
static mp_obj_t pk_to_pem_private(mbedtls_pk_context *pk) {
    unsigned char buf[PEM_BUF_SIZE];
    memset(buf, 0, sizeof(buf));

    int ret = mbedtls_pk_write_key_pem(pk, buf, sizeof(buf));
    if (ret != 0) {
        raise_mbedtls_error(ret, "pk_write_key_pem");
    }
    return mp_obj_new_str((const char *)buf, strlen((const char *)buf));
}

/* Helper: export public key in PEM format */
static mp_obj_t pk_to_pem_public(mbedtls_pk_context *pk) {
    unsigned char buf[PEM_BUF_SIZE];
    memset(buf, 0, sizeof(buf));

    int ret = mbedtls_pk_write_pubkey_pem(pk, buf, sizeof(buf));
    if (ret != 0) {
        raise_mbedtls_error(ret, "pk_write_pubkey_pem");
    }
    return mp_obj_new_str((const char *)buf, strlen((const char *)buf));
}


/*
 * generate_ec_keypair(curve_name="secp256r1")
 *
 * Generate a pair of EC keys. Supported curves: "secp256r1" (default), "secp384r1", "secp521r1"
 * supported curves: "secp256r1" (default), "secp384r1", "secp521r1"
 * Returns: (private_key_pem, public_key_pem)
 */
STATIC mp_obj_t x509gen_generate_ec_keypair(size_t n_args, const mp_obj_t *args) {
    
    const char *curve_name = "secp256r1";
    if (n_args >= 1) {
        curve_name = mp_obj_str_get_str(args[0]);
    }

    mbedtls_ecp_group_id gid;
    if (strcmp(curve_name, "secp256r1") == 0) {
        gid = MBEDTLS_ECP_DP_SECP256R1;
    } else if (strcmp(curve_name, "secp384r1") == 0) {
        gid = MBEDTLS_ECP_DP_SECP384R1;
    } else if (strcmp(curve_name, "secp521r1") == 0) {
        gid = MBEDTLS_ECP_DP_SECP521R1;
    } else {
        mp_raise_ValueError(MP_ERROR_TEXT("Curva non supportata. Usa: secp256r1, secp384r1, secp521r1"));
        return mp_const_none; /* unreachable */
    }

    mbedtls_pk_context pk;
    mbedtls_entropy_context entropy;
    mbedtls_ctr_drbg_context drbg;

    mbedtls_pk_init(&pk);

    int ret = init_rng(&entropy, &drbg);
    if (ret != 0) {
        raise_mbedtls_error(ret, "ctr_drbg_seed");
    }

    /* Setup Key type EC */
    ret = mbedtls_pk_setup(&pk, mbedtls_pk_info_from_type(MBEDTLS_PK_ECKEY));
    if (ret != 0) {
        cleanup_rng(&entropy, &drbg);
        raise_mbedtls_error(ret, "pk_setup(EC)");
    }

    /* Generate the key pair */
    ret = mbedtls_ecp_gen_key(gid, mbedtls_pk_ec(pk),
                               mbedtls_ctr_drbg_random, &drbg);
    if (ret != 0) {
        mbedtls_pk_free(&pk);
        cleanup_rng(&entropy, &drbg);
        raise_mbedtls_error(ret, "ecp_gen_key");
    }

    /* Export in PEM format */
    mp_obj_t priv_pem = pk_to_pem_private(&pk);
    mp_obj_t pub_pem  = pk_to_pem_public(&pk);

    /* Cleanup */
    mbedtls_pk_free(&pk);
    cleanup_rng(&entropy, &drbg);

    /* Returns tuple (private, public) */
    mp_obj_t tuple[2] = { priv_pem, pub_pem };
    return mp_obj_new_tuple(2, tuple);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(x509gen_generate_ec_keypair_obj, 0, 1, x509gen_generate_ec_keypair);


/*
 * generate_rsa_keypair(bits=2048)
 *
 * Generate a pair of RSA keys.
 * ATTENZIONE: RSA-2048 può richiedere 10-30 secondi sull'RP2350!
 * Returns: (private_key_pem, public_key_pem)
 */
STATIC mp_obj_t x509gen_generate_rsa_keypair(size_t n_args, const mp_obj_t *args) {
    int bits = 2048;
    if (n_args >= 1) {
        bits = mp_obj_get_int(args[0]);
        if (bits < 1024 || bits > 4096) {
            mp_raise_ValueError(MP_ERROR_TEXT("RSA bits deve essere 1024-4096"));
        }
    }

    mbedtls_pk_context pk;
    mbedtls_entropy_context entropy;
    mbedtls_ctr_drbg_context drbg;

    mbedtls_pk_init(&pk);

    int ret = init_rng(&entropy, &drbg);
    if (ret != 0) {
        raise_mbedtls_error(ret, "ctr_drbg_seed");
    }

    ret = mbedtls_pk_setup(&pk, mbedtls_pk_info_from_type(MBEDTLS_PK_RSA));
    if (ret != 0) {
        cleanup_rng(&entropy, &drbg);
        raise_mbedtls_error(ret, "pk_setup(RSA)");
    }

    ret = mbedtls_rsa_gen_key(mbedtls_pk_rsa(pk), mbedtls_ctr_drbg_random,
                               &drbg, bits, 65537);
    if (ret != 0) {
        mbedtls_pk_free(&pk);
        cleanup_rng(&entropy, &drbg);
        raise_mbedtls_error(ret, "rsa_gen_key");
    }

    mp_obj_t priv_pem = pk_to_pem_private(&pk);
    mp_obj_t pub_pem  = pk_to_pem_public(&pk);

    mbedtls_pk_free(&pk);
    cleanup_rng(&entropy, &drbg);

    mp_obj_t tuple[2] = { priv_pem, pub_pem };
    return mp_obj_new_tuple(2, tuple);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(x509gen_generate_rsa_keypair_obj, 0, 1, x509gen_generate_rsa_keypair);


/* 
 * generate_self_signed_cert(
 *     private_key_pem,
 *     subject="CN=RP2350,O=MyOrg",
 *     serial=1,
 *     not_before="20250101000000",    # YYYYMMDDHHMMSS
 *     not_after="20350101000000",
 *     is_ca=False,
 *     key_usage=0                      # bit mask, 0 = default
 * )
 *
 * Genera un certificato X.509 v3 self-signed.
 * Ritorna: cert_pem (stringa)
 */
STATIC mp_obj_t x509gen_generate_self_signed_cert(size_t n_args, const mp_obj_t *args,
                                                   mp_map_t *kw_args) {
    /* Positional arguments */
    enum {
        ARG_private_key_pem,
        ARG_subject,
        ARG_serial,
        ARG_not_before,
        ARG_not_after,
        ARG_is_ca,
        ARG_key_usage,
        ARG_md_alg,
    };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_private_key_pem, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_subject,         MP_ARG_KW_ONLY | MP_ARG_OBJ,
          {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_serial,          MP_ARG_KW_ONLY | MP_ARG_OBJ,
          {.u_obj = MP_OBJ_NEW_SMALL_INT(1)} },
        { MP_QSTR_not_before,      MP_ARG_KW_ONLY | MP_ARG_OBJ,
          {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_not_after,       MP_ARG_KW_ONLY | MP_ARG_OBJ,
          {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_is_ca,           MP_ARG_KW_ONLY | MP_ARG_BOOL,
          {.u_bool = false} },
        { MP_QSTR_key_usage,       MP_ARG_KW_ONLY | MP_ARG_INT,
          {.u_int = 0} },
        { MP_QSTR_md_alg,          MP_ARG_KW_ONLY | MP_ARG_OBJ,
          {.u_obj = MP_OBJ_NULL} },
    };

    mp_arg_val_t parsed[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all(n_args, args, kw_args,
                     MP_ARRAY_SIZE(allowed_args), allowed_args, parsed);

    /* Extract the private key PEM */
    const char *key_pem = mp_obj_str_get_str(parsed[ARG_private_key_pem].u_obj);

    /* Subject DN (default) */
    const char *subject = "CN=RP2350-Device,O=Embedded";
    if (parsed[ARG_subject].u_obj != MP_OBJ_NULL) {
        subject = mp_obj_str_get_str(parsed[ARG_subject].u_obj);
    }

    /* Serial number as string (mbedTLS wants a decimal string) */
    char serial_str[24];
    int serial_val = mp_obj_get_int(parsed[ARG_serial].u_obj);
    snprintf(serial_str, sizeof(serial_str), "%d", serial_val);

    /* Validity: format "YYYYMMDDHHMMSS" */
    const char *not_before = "20250101000000";
    const char *not_after  = "20350101000000";
    if (parsed[ARG_not_before].u_obj != MP_OBJ_NULL) {
        not_before = mp_obj_str_get_str(parsed[ARG_not_before].u_obj);
    }
    if (parsed[ARG_not_after].u_obj != MP_OBJ_NULL) {
        not_after = mp_obj_str_get_str(parsed[ARG_not_after].u_obj);
    }

    bool is_ca = parsed[ARG_is_ca].u_bool;
    int key_usage = parsed[ARG_key_usage].u_int;

    /* Hash algorithm */
    mbedtls_md_type_t md_alg = MBEDTLS_MD_SHA256;
    if (parsed[ARG_md_alg].u_obj != MP_OBJ_NULL) {
        const char *md_name = mp_obj_str_get_str(parsed[ARG_md_alg].u_obj);
        if (strcmp(md_name, "sha256") == 0) {
            md_alg = MBEDTLS_MD_SHA256;
        } else if (strcmp(md_name, "sha384") == 0) {
            md_alg = MBEDTLS_MD_SHA384;
        } else if (strcmp(md_name, "sha512") == 0) {
            md_alg = MBEDTLS_MD_SHA512;
        } else {
            mp_raise_ValueError(MP_ERROR_TEXT("md_alg: usa sha256, sha384, sha512"));
        }
    }

    /* ---- Initialization of mbedTLS contexts ---- */
    mbedtls_pk_context issuer_key;
    mbedtls_x509write_cert crt;
    mbedtls_entropy_context entropy;
    mbedtls_ctr_drbg_context drbg;
    mbedtls_mpi serial_mpi;

    mbedtls_pk_init(&issuer_key);
    mbedtls_x509write_crt_init(&crt);
    mbedtls_mpi_init(&serial_mpi);

    int ret = init_rng(&entropy, &drbg);
    if (ret != 0) {
        raise_mbedtls_error(ret, "ctr_drbg_seed");
    }

    /* Parse private key PEM */
    ret = mbedtls_pk_parse_key(&issuer_key,
                                (const unsigned char *)key_pem,
                                strlen(key_pem) + 1,  /* +1 per il null terminator */
                                NULL, 0,
                                mbedtls_ctr_drbg_random, &drbg);
    if (ret != 0) {
        cleanup_rng(&entropy, &drbg);
        mbedtls_pk_free(&issuer_key);
        mbedtls_x509write_crt_free(&crt);
        raise_mbedtls_error(ret, "pk_parse_key");
    }

    /* Configure the certificate */
    mbedtls_x509write_crt_set_version(&crt, MBEDTLS_X509_CRT_VERSION_3);
    mbedtls_x509write_crt_set_md_alg(&crt, md_alg);

    /* Serial number */
	ret = mbedtls_mpi_read_string(&serial_mpi, 10, serial_str);
	if (ret != 0) {
	    goto cleanup_cert;
	}

	/* Convert MPI to byte buffer */
	unsigned char serial_buf[20];  // 20 byte bastano per un serial number
	size_t serial_len = mbedtls_mpi_size(&serial_mpi);
	if (serial_len > sizeof(serial_buf)) {
	    serial_len = sizeof(serial_buf);
	}

	ret = mbedtls_mpi_write_binary(&serial_mpi, serial_buf, serial_len);
	if (ret != 0) {
	    goto cleanup_cert;
	}

	ret = mbedtls_x509write_crt_set_serial_raw(&crt, serial_buf, serial_len);
	if (ret != 0) {
	    goto cleanup_cert;
	}

    /* Validity */
    ret = mbedtls_x509write_crt_set_validity(&crt, not_before, not_after);
    if (ret != 0) {
        goto cleanup_cert;
    }

    /* Issuer = Subject (self-signed) */
    ret = mbedtls_x509write_crt_set_issuer_name(&crt, subject);
    if (ret != 0) {
        goto cleanup_cert;
    }
    ret = mbedtls_x509write_crt_set_subject_name(&crt, subject);
    if (ret != 0) {
        goto cleanup_cert;
    }

    /* Keys */
    mbedtls_x509write_crt_set_subject_key(&crt, &issuer_key);
    mbedtls_x509write_crt_set_issuer_key(&crt, &issuer_key);

    /* Extensions: Basic Constraints */
    ret = mbedtls_x509write_crt_set_basic_constraints(&crt, is_ca ? 1 : 0,
                                                       is_ca ? -1 : 0);
    if (ret != 0) {
        goto cleanup_cert;
    }

    /* Subject Key Identifier */
    ret = mbedtls_x509write_crt_set_subject_key_identifier(&crt);
    if (ret != 0) {
        goto cleanup_cert;
    }

    /* Authority Key Identifier */
    ret = mbedtls_x509write_crt_set_authority_key_identifier(&crt);
    if (ret != 0) {
        goto cleanup_cert;
    }

    /* Key Usage (opzionale) */
    if (key_usage != 0) {
        ret = mbedtls_x509write_crt_set_key_usage(&crt, key_usage);
        if (ret != 0) {
            goto cleanup_cert;
        }
    }

    /* ---- Write the certificate in PEM format ---- */
    {
        unsigned char pem_buf[PEM_BUF_SIZE];
        memset(pem_buf, 0, sizeof(pem_buf));

        ret = mbedtls_x509write_crt_pem(&crt, pem_buf, sizeof(pem_buf),
                                         mbedtls_ctr_drbg_random, &drbg);
        if (ret != 0) {
            goto cleanup_cert;
        }

        /* Cleanup and return */
        mbedtls_mpi_free(&serial_mpi);
        mbedtls_x509write_crt_free(&crt);
        mbedtls_pk_free(&issuer_key);
        cleanup_rng(&entropy, &drbg);

        return mp_obj_new_str((const char *)pem_buf, strlen((const char *)pem_buf));
    }

cleanup_cert:
    mbedtls_mpi_free(&serial_mpi);
    mbedtls_x509write_crt_free(&crt);
    mbedtls_pk_free(&issuer_key);
    cleanup_rng(&entropy, &drbg);
    raise_mbedtls_error(ret, "x509write_crt");
    return mp_const_none; /* unreachable */
}
STATIC MP_DEFINE_CONST_FUN_OBJ_KW(x509gen_generate_self_signed_cert_obj, 1,
                                   x509gen_generate_self_signed_cert);


/*
 * generate_csr(
 *     private_key_pem,
 *     subject="CN=RP2350,O=MyOrg",
 *     md_alg="sha256"
 * )
 *
 * Generates a Certificate Signing Request (CSR) in PEM format.
 * Useful for requesting a certificate from an external CA.
 * Returns: csr_pem (string)
 */
STATIC mp_obj_t x509gen_generate_csr(size_t n_args, const mp_obj_t *args,
                                      mp_map_t *kw_args) {
    enum {
        ARG_private_key_pem,
        ARG_subject,
        ARG_md_alg,
    };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_private_key_pem, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_subject,         MP_ARG_KW_ONLY | MP_ARG_OBJ,
          {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_md_alg,          MP_ARG_KW_ONLY | MP_ARG_OBJ,
          {.u_obj = MP_OBJ_NULL} },
    };

    mp_arg_val_t parsed[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all(n_args, args, kw_args,
                     MP_ARRAY_SIZE(allowed_args), allowed_args, parsed);

    const char *key_pem = mp_obj_str_get_str(parsed[ARG_private_key_pem].u_obj);

    const char *subject = "CN=RP2350-Device,O=Embedded";
    if (parsed[ARG_subject].u_obj != MP_OBJ_NULL) {
        subject = mp_obj_str_get_str(parsed[ARG_subject].u_obj);
    }

    mbedtls_md_type_t md_alg = MBEDTLS_MD_SHA256;
    if (parsed[ARG_md_alg].u_obj != MP_OBJ_NULL) {
        const char *md_name = mp_obj_str_get_str(parsed[ARG_md_alg].u_obj);
        if (strcmp(md_name, "sha256") == 0)      md_alg = MBEDTLS_MD_SHA256;
        else if (strcmp(md_name, "sha384") == 0)  md_alg = MBEDTLS_MD_SHA384;
        else if (strcmp(md_name, "sha512") == 0)  md_alg = MBEDTLS_MD_SHA512;
        else mp_raise_ValueError(MP_ERROR_TEXT("md_alg: usa sha256, sha384, sha512"));
    }

    mbedtls_pk_context pk;
    mbedtls_x509write_csr csr;
    mbedtls_entropy_context entropy;
    mbedtls_ctr_drbg_context drbg;

    mbedtls_pk_init(&pk);
    mbedtls_x509write_csr_init(&csr);

    int ret = init_rng(&entropy, &drbg);
    if (ret != 0) {
        raise_mbedtls_error(ret, "ctr_drbg_seed");
    }

    /* Parse private key */
    ret = mbedtls_pk_parse_key(&pk,
                                (const unsigned char *)key_pem,
                                strlen(key_pem) + 1,
                                NULL, 0,
                                mbedtls_ctr_drbg_random, &drbg);
    if (ret != 0) {
        cleanup_rng(&entropy, &drbg);
        mbedtls_pk_free(&pk);
        mbedtls_x509write_csr_free(&csr);
        raise_mbedtls_error(ret, "pk_parse_key");
    }

    /* Configure CSR */
    mbedtls_x509write_csr_set_md_alg(&csr, md_alg);
    mbedtls_x509write_csr_set_key(&csr, &pk);

    ret = mbedtls_x509write_csr_set_subject_name(&csr, subject);
    if (ret != 0) {
        mbedtls_pk_free(&pk);
        mbedtls_x509write_csr_free(&csr);
        cleanup_rng(&entropy, &drbg);
        raise_mbedtls_error(ret, "csr_set_subject_name");
    }

    /* Write CSR in PEM */
    unsigned char pem_buf[PEM_BUF_SIZE];
    memset(pem_buf, 0, sizeof(pem_buf));

    ret = mbedtls_x509write_csr_pem(&csr, pem_buf, sizeof(pem_buf),
                                     mbedtls_ctr_drbg_random, &drbg);
    if (ret != 0) {
        mbedtls_pk_free(&pk);
        mbedtls_x509write_csr_free(&csr);
        cleanup_rng(&entropy, &drbg);
        raise_mbedtls_error(ret, "x509write_csr_pem");
    }

    mbedtls_pk_free(&pk);
    mbedtls_x509write_csr_free(&csr);
    cleanup_rng(&entropy, &drbg);

    return mp_obj_new_str((const char *)pem_buf, strlen((const char *)pem_buf));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_KW(x509gen_generate_csr_obj, 1, x509gen_generate_csr);


/* 
 * Costant Key Usage expose to microPython
 * 
 */


/* 
 * Registrazione del modulo
 */
STATIC const mp_rom_map_elem_t x509gen_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__),               MP_ROM_QSTR(MP_QSTR_x509gen) },

    /* functions */
    { MP_ROM_QSTR(MP_QSTR_generate_ec_keypair),     MP_ROM_PTR(&x509gen_generate_ec_keypair_obj) },
    { MP_ROM_QSTR(MP_QSTR_generate_rsa_keypair),    MP_ROM_PTR(&x509gen_generate_rsa_keypair_obj) },
    { MP_ROM_QSTR(MP_QSTR_generate_self_signed_cert), MP_ROM_PTR(&x509gen_generate_self_signed_cert_obj) },
    { MP_ROM_QSTR(MP_QSTR_generate_csr),            MP_ROM_PTR(&x509gen_generate_csr_obj) },

    /* Costants Key Usage */
    { MP_ROM_QSTR(MP_QSTR_KU_DIGITAL_SIGNATURE), MP_ROM_INT(MBEDTLS_X509_KU_DIGITAL_SIGNATURE) },
    { MP_ROM_QSTR(MP_QSTR_KU_KEY_ENCIPHERMENT),  MP_ROM_INT(MBEDTLS_X509_KU_KEY_ENCIPHERMENT) },
    { MP_ROM_QSTR(MP_QSTR_KU_DATA_ENCIPHERMENT), MP_ROM_INT(MBEDTLS_X509_KU_DATA_ENCIPHERMENT) },
    { MP_ROM_QSTR(MP_QSTR_KU_KEY_AGREEMENT),     MP_ROM_INT(MBEDTLS_X509_KU_KEY_AGREEMENT) },
    { MP_ROM_QSTR(MP_QSTR_KU_KEY_CERT_SIGN),     MP_ROM_INT(MBEDTLS_X509_KU_KEY_CERT_SIGN) },
    { MP_ROM_QSTR(MP_QSTR_KU_CRL_SIGN),          MP_ROM_INT(MBEDTLS_X509_KU_CRL_SIGN) },
};
STATIC MP_DEFINE_CONST_DICT(x509gen_module_globals, x509gen_module_globals_table);

const mp_obj_module_t mp_module_x509gen = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&x509gen_module_globals,
};

/* Register the module as built-in */
MP_REGISTER_MODULE(MP_QSTR_x509gen, mp_module_x509gen);
