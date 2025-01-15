import random

public_key = (65537, 33043)
private_key = (23633, 33043)

def is_prime(n):
    """判断一个数是否为质数"""
    if n < 2:
        return False
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            return False
    return True


def generate_prime(min_value, max_value):
    """生成指定范围内的随机质数"""
    prime = random.randint(min_value, max_value)
    while not is_prime(prime):
        prime = random.randint(min_value, max_value)
    return prime


def mod_inverse(e, phi):
    """计算模反元素"""

    def extended_gcd(a, b):
        if a == 0:
            return b, 0, 1
        gcd, x1, y1 = extended_gcd(b % a, a)
        x = y1 - (b // a) * x1
        y = x1
        return gcd, x, y

    gcd, x, _ = extended_gcd(e, phi)
    if gcd != 1:
        raise ValueError("模反元素不存在")
    return x % phi


def generate_keypair():
    """生成公钥和私钥对"""
    # 选择两个不同的质数
    p = generate_prime(100, 300)
    q = generate_prime(100, 300)
    while p == q:
        q = generate_prime(100, 300)

    # 计算n和欧拉函数φ(n)
    n = p * q
    phi = (p - 1) * (q - 1)

    # 选择公钥e
    e = 65537  # 常用的公钥指数
    while e < phi:
        if math.gcd(e, phi) == 1:
            break
        e += 2

    # 计算私钥d
    d = mod_inverse(e, phi)

    return ((e, n), (d, n))


def encrypt(plaintext):
    """使用公钥加密消息"""
    e, n = public_key
    # 将消息转换为数字
    cipher = [pow(ord(char), e, n) for char in plaintext]
    return cipher


def decrypt(ciphertext):
    """使用私钥解密消息"""
    d, n = private_key
    # 解密并转换回字符
    plaintext = [chr(pow(char, d, n)) for char in ciphertext]
    return ''.join(plaintext)


# 使用示例
if __name__ == "__main__":
    # 生成密钥对

    print(f"公钥: {public_key}")
    print(f"私钥: {private_key}")

    # 要加密的消息
    # message = "Hello, RSA!"
    # print(f"原始消息: {message}")

    # 加密
    # encrypted_msg = encrypt(public_key, message)
    encrypted_msg = [9685, 31316, 11552, 11552, 27074]
    print(f"加密后: {encrypted_msg}")

    # 解密
    decrypted_msg = decrypt(private_key, encrypted_msg)
    print(f"解密后: {decrypted_msg}")
