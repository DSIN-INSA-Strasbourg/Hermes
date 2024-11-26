<!--
Hermes : Change Data Capture (CDC) tool from any source(s) to any target
Copyright (C) 2024 INSA Strasbourg

This file is part of Hermes.

Hermes is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Hermes is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Hermes. If not, see <https://www.gnu.org/licenses/>.
-->

# Plugin d'attribut `crypto_RSA_OAEP`

## Description

Ce plugin permet de chiffrer/déchiffrer des chaînes avec des clés RSA asymétriques, en utilisant PKCS#1 OAEP, un chiffrement asymétrique basé sur RSA et le remplissage OAEP.

## Configuration

Vous pouvez configurer autant de clés que vous le souhaitez dans les paramètres du plugin. Une clé peut être utilisée pour chiffrer ou déchiffrer, mais pas les deux. Le plugin déterminera s'il s'agit d'une opération de chiffrement ou de déchiffrement en fonction du type de clé : déchiffrement pour les clés privées et chiffrement pour les clés publiques.

```yaml
hermes:
  plugins:
    attributes:
      crypto_RSA_OAEP:
        settings:
          keys:
            # Nom de la clé, vous pouvez définir ce que vous voulez
            encrypt_to_messagebus:
              # Type de hachage, lors du déchiffrement, vous devez évidemment
              # utiliser la même valeur qui a été utilisée pour le chiffrement
              hash: SHA3_512
              # Clé publique RSA utilisée pour chiffrer
              # ATTENTION - CETTE CLÉ EST FAIBLE ET PUBLIQUE, NE L'UTILISEZ JAMAIS
              rsa_key: |-
                  -----BEGIN PUBLIC KEY-----
                  MCgCIQCy2W1bAPOa1JIeLuV8qq1Qg7h0jxpf8QCik11H9xZcfwIDAQAB
                  -----END PUBLIC KEY-----

            # Une autre clé
            decrypt_from_messagebus:
              hash: SHA3_512
              # Clé privée RSA utilisée pour déchiffrer
              # ATTENTION - CETTE CLÉ EST FAIBLE ET PUBLIQUE, NE L'UTILISEZ JAMAIS
              rsa_key: |-
                  -----BEGIN RSA PRIVATE KEY-----
                  MIGrAgEAAiEAstltWwDzmtSSHi7lfKqtUIO4dI8aX/EAopNdR/cWXH8CAwEAAQIh
                  AKfflFjGNOJQwvJX3Io+/juxO+HFd7SRC++zBD9paZqZAhEA5OtjZQUapRrV/aC5
                  NXFsswIRAMgBtgpz+t0FxyEXdzlcTwUCEHU6WZ8M2xU7xePpH49Ps2MCEQC+78s+
                  /WvfNtXcRI+gJfyVAhAjcIWzHC5q4wzgL7psbPGy
                  -----END RSA PRIVATE KEY-----
```

Les valeurs valides pour `hash` sont :

- SHA224
- SHA256
- SHA384
- SHA512
- SHA3_224
- SHA3_256
- SHA3_384
- SHA3_512

## Utilisation

```python
crypto_RSA_OAEP(value: bytes | str, keyname: str) → str
```

Une fois que tout est configuré, vous pouvez chiffrer les données avec la clé `encrypt_to_messagebus` comme ceci dans un filtre Jinja :

```yaml
password_encrypted: "{{ PASSWORD_CLEAR | crypto_RSA_OAEP('encrypt_to_messagebus') }}"
password_decrypted: "{{ PASSWORD_ENCRYPTED | crypto_RSA_OAEP('decrypt_from_messagebus') }}"
```

Vous pouvez même déchiffrer et rechiffrer immédiatement les données avec une autre clé comme ceci :

```yaml
password_reencrypted: "{{ PASSWORD_ENCRYPTED | crypto_RSA_OAEP('decrypt_from_datasource') | crypto_RSA_OAEP('encrypt_to_messagebus') }}"
```
