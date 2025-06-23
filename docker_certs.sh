#!/bin/bash

# =============== 配置区域 ===============
SERVER_IP=""            # 服务器IP地址        
CA_PASSWORD="password"       # CA私钥的加密密码
CA_EMAIL=""               # CA私钥的邮箱           
CERT_VALIDITY_DAYS=365     # 证书有效期（天）


# 服务器证书配置
SERVER_IPS=("$SERVER_IP" "127.0.0.1")  # 所有服务器IP地址
DNS_ALT="223.5.5.5,8.8.8.8"     # 额外的DNS名称
SUBJECT="/C=CN/ST=Shanghai/L=Shanghai/O=MAO/OU=Department/emailAddress=$CA_EMAIL"


# =======================================

# 清理旧文件
rm -f ca-key.pem ca.pem server-key.pem server.csr server-cert.pem \
      client-key.pem client.csr client-cert.pem \
      extfile.cnf extfile-client.cnf ca.srl

# 1. 生成加密的CA私钥
echo "生成CA私钥..."
openssl genrsa -aes256 -passout pass:"$CA_PASSWORD" -out ca-key.pem 4096

# 2. 生成CA证书
echo "生成CA证书..."
openssl req -new -x509 -days $CERT_VALIDITY_DAYS -key ca-key.pem -passin pass:"$CA_PASSWORD" \
    -sha256 -out ca.pem -subj "$SUBJECT"

# 3. 生成服务器私钥
echo "生成服务器私钥..."
openssl genrsa -out server-key.pem 4096

# 4. 创建服务器证书请求（使用第一个IP作为CN）
SERVER_CN=${SERVER_IPS[0]}
echo "创建服务器证书请求 (CN=$SERVER_CN)..."
openssl req -subj "$SERVER_SUBJECT/CN=$SERVER_CN" -sha256 \
    -new -key server-key.pem -out server.csr

# 5. 创建扩展配置文件 - 所有值在一行内用逗号分隔
echo "创建服务器证书扩展配置..."
alt_names=""
if [ -n "$DNS_ALT" ]; then
    # 添加所有DNS名称
    IFS=',' read -ra DNS_ARRAY <<< "$DNS_ALT"
    for dns in "${DNS_ARRAY[@]}"; do
        alt_names="${alt_names}DNS:$dns,"
    done
fi

# 添加所有IP地址
for ip in "${SERVER_IPS[@]}"; do
    alt_names="${alt_names}IP:$ip,"
done

# 删除末尾的逗号
alt_names=${alt_names%,}
echo "subjectAltName = $alt_names" > extfile.cnf
echo "extendedKeyUsage = serverAuth" >> extfile.cnf

# 6. 生成服务器证书
echo "生成服务器证书..."
openssl x509 -req -days $CERT_VALIDITY_DAYS -sha256 \
    -in server.csr -CA ca.pem -CAkey ca-key.pem -passin pass:"$CA_PASSWORD" \
    -CAcreateserial -out server-cert.pem -extfile extfile.cnf

# 7. 生成客户端私钥
echo "生成客户端私钥..."
openssl genrsa -out client-key.pem 4096

# 8. 创建客户端证书请求
echo "创建客户端证书请求..."
openssl req -subj "$CLIENT_SUBJECT/CN=client" -new \
    -key client-key.pem -out client.csr

# 9. 创建客户端扩展配置
echo "extendedKeyUsage = clientAuth" > extfile-client.cnf

# 10. 生成客户端证书
echo "生成客户端证书..."
openssl x509 -req -days $CERT_VALIDITY_DAYS -sha256 \
    -in client.csr -CA ca.pem -CAkey ca-key.pem -passin pass:"$CA_PASSWORD" \
    -CAcreateserial -out client-cert.pem -extfile extfile-client.cnf

# 设置文件权限
chmod 0400 ca-key.pem server-key.pem client-key.pem
chmod 0444 ca.pem server-cert.pem client-cert.pem

# 验证证书
echo -e "\n证书验证:"
echo "CA证书:"
openssl x509 -in ca.pem -text -noout | grep -E "Issuer:|Subject:|Not After"
echo -e "\n服务器证书:"
openssl x509 -in server-cert.pem -text -noout | grep -E "Issuer:|Subject:|DNS:|IP Address:|Not After"
echo -e "\n客户端证书:"
openssl x509 -in client-cert.pem -text -noout | grep -E "Issuer:|Subject:|Not After"

echo -e "\n证书生成完成！"
echo "CA证书: ca.pem"
echo "服务器证书: server-cert.pem"
echo "客户端证书: client-cert.pem"
