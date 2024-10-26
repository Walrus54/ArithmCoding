import filecmp
from collections import Counter

def calc_cum_freq(probs):
    cum_freq = [0.0]
    for symbol in probs.values():
        cum_freq.append(cum_freq[-1] + symbol)
    cum_freq.pop()
    cum_freq = {k: v for k, v in zip(probs.keys(), cum_freq)}
    return cum_freq

def arith_encode(src_bytes, byte_freq):
    h = 2**32 - 1 
    qtr = (h + 1) / 4
    thr = qtr * 3
    half = qtr * 2
    probs = calc_probs(byte_freq, len(src_bytes))
    cum_freq = calc_cum_freq(probs)
    enc_nums = []
    lower_bound, upper_bound = 0, h
    straddle = 0

    for byte in src_bytes:
        range_width = upper_bound - lower_bound + 1
        lower_bound += int((range_width * cum_freq[byte]) // 1)  
        upper_bound = lower_bound + int((range_width * probs[byte]) // 1) 

        while True:
            if upper_bound < half:
                enc_nums.append(0)
                enc_nums.extend([1] * straddle)
                straddle = 0
            elif lower_bound >= half:
                enc_nums.append(1)
                enc_nums.extend([0] * straddle)
                straddle = 0
                lower_bound -= half
                upper_bound -= half
            elif lower_bound >= qtr and upper_bound < thr:
                straddle += 1
                lower_bound -= qtr
                upper_bound -= qtr
            else:
                break
            lower_bound *= 2
            upper_bound = 2 * upper_bound + 1

    enc_nums.extend([0] + [1] * straddle if lower_bound < qtr else [1] + [0] * straddle)
    return enc_nums

def arith_decode(enc_nums, prob_model, text_len):
    bp = 32
    h = 2**32 - 1 
    qtr = (h + 1) / 4
    thr = qtr * 3
    half = qtr * 2

    alphabet = list(prob_model)
    cum_freq = [0]
    for symbol_index in prob_model:
        cum_freq.append(cum_freq[-1] + prob_model[symbol_index])
    cum_freq.pop()

    prob_model = list(prob_model.values())

    enc_nums.extend(bp * [0])
    dec_symbols = text_len * [0]

    current_value = int(''.join(str(a) for a in enc_nums[0:bp]), 2)
    bit_position = bp
    lower_bound, upper_bound = 0, h

    dec_position = 0
    while True:
        current_range = upper_bound - lower_bound + 1
        symbol_index = find_idx(cum_freq, (current_value - lower_bound) / current_range) - 1
        dec_symbols[dec_position] = alphabet[symbol_index]

        lower_bound += int((cum_freq[symbol_index] * current_range) // 1)  
        upper_bound = lower_bound + int((prob_model[symbol_index] * current_range) // 1)

        while True:
            if upper_bound < half:
                pass
            elif lower_bound >= half:
                lower_bound -= half
                upper_bound -= half
                current_value -= half
            elif lower_bound >= qtr and upper_bound < thr:
                lower_bound -= qtr
                upper_bound -= qtr
                current_value -= qtr
            else:
                break
            lower_bound *= 2
            upper_bound = 2 * upper_bound + 1
            current_value = 2 * current_value + enc_nums[bit_position]
            bit_position += 1
            if bit_position == len(enc_nums)+1:
                break

        dec_position += 1
        if dec_position == text_len or bit_position == len(enc_nums) +1:
            break
    return bytes(dec_symbols)

def find_idx(lst, val):
    for i, item in enumerate(lst):
      if item >= val:
        return i
    return 0

def calc_probs(char_cnt, txt_len):
  probs = {}
  for char, count in char_cnt.items():
    probs[char] = count / txt_len
  return probs

def encode(fname_in, fname_out):
    with open(fname_in, "rb") as f:
        text = f.read()
    len_txt = len(text)
    last_sim = text[-1]
    dictionary = Counter(text)
    enc = arith_encode(text, dictionary)
    padding = 8 - len(enc) % 8
    enc += [0] * padding
    encoded_bytes = bytes(int(''.join(map(str, enc[i:i+8])), 2) for i in range(0, len(enc), 8))
    with open(fname_out, "wb") as f:
        f.write(len_txt.to_bytes(4, 'little'))
        f.write(len(dictionary).to_bytes(1, 'little'))
        f.write(padding.to_bytes(1, 'little'))
        f.write(b"".join([bytes([byte]) + freq.to_bytes(4, 'big') for byte, freq in dictionary.items()]))
        f.write(encoded_bytes)
        f.write(bytes([last_sim]))

def decode(fname_in, fname_out):
    with open(fname_in, "rb") as f:
        txt_len, slo_len, new_padding = [int.from_bytes(f.read(n), 'little') for n in (4, 1, 1)]
        new_slov = {int.from_bytes(f.read(1), 'little'): int.from_bytes(f.read(4), 'big') for _ in range(slo_len)}
        data_bits = f.read()
        encoded_text = ''.join([bin(byte)[2:].rjust(8, '0') for byte in data_bits])[:-new_padding]
        new_last_sim = data_bits[-1]
    encoded_txt = [int(bit) for bit in encoded_text]
    decoded_text = arith_decode(encoded_txt, calc_probs(new_slov, txt_len), txt_len)
    decoded_text = bytearray(decoded_text)
    decoded_text[-1] = new_last_sim
    decoded_text = bytes(decoded_text)
    with open(fname_out, "wb") as f:
        f.write(decoded_text)

def main():
    while True:
        mode = input("Choose mode (encode(1)/decode(2)/exit(3)): ")
        if mode == "1":
            fname_in1 = 'input.txt'
            fname_out1 = 'encode.txt'
            encode(fname_in1, fname_out1)
            print("Encoded string written to", fname_out1)
        elif mode == "2":
            fname_in = 'encode.txt'
            fname_out = 'decode.txt'
            decode(fname_in, fname_out)
            print("Decoded string written to", fname_out)
            print(filecmp.cmp(fname_in1, fname_out, shallow=True))
        elif mode == "3":
            break
        else:
            print("Invalid mode. Please choose 'encode(1)', 'decode(2)', or 'exit(3)'.")

if __name__ == "__main__":
    main()