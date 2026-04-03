/*
 * mbedtls_config_board.h — nXPico M board-specific mbedTLS configuration
 *
 * Extends the standard rp2 port mbedTLS config with features required
 * by the x509gen C module (X.509 certificate and CSR generation).
 */

#ifndef NXPICO_M_MBEDTLS_CONFIG_BOARD_H
#define NXPICO_M_MBEDTLS_CONFIG_BOARD_H

/* Include standard rp2 port configuration */
#include "ports/rp2/mbedtls/mbedtls_config_port.h"

/* Enable x509 write features needed by the x509gen module */
#include "ports/rp2/boards/NXPICO_M/cmodules/nxpico/mbedtls_config_x509gen.h"

#endif /* NXPICO_M_MBEDTLS_CONFIG_BOARD_H */
