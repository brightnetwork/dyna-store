import { decode } from "hi-base32";

const BASE62 = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";

const b62_decode_int = (str: string) => {
  const base = BASE62.length;
  const strlen = str.length;
  let num = 0;
  for (let idx = 0; idx < strlen; idx++) {
    const power = strlen - (idx + 1);
    num += BASE62.indexOf(str[idx]) * base ** power;
  }
  return num;
};

const b62_decode_np_float_32 = (str: string) => {
  const int = b62_decode_int(str);
  let buffer = new ArrayBuffer(4);
  let view = new DataView(buffer);
  view.setUint32(0, int, true);
  let floatValue = view.getFloat32(0, true);
  return floatValue;
};

type HCFField = {
  __hcf: boolean;
  i: number;
  l: number;
  t: "int" | "datetime" | "str" | "NoneType" | "float";
};

const isHCFField = (value: unknown): value is HCFField => {
  if (typeof value === "object") {
    return value?.hasOwnProperty("__hcf") ?? false;
  }
  return false;
};

export const parse = (
  id: string,
  metadata: Record<string, unknown>,
): Record<string, unknown> => {
  const toReturn: Record<string, unknown> = {};
  for (const key of Object.keys(metadata)) {
    const value = metadata[key];
    if (isHCFField(value)) {
      const encoded_value = id.slice(value.i, value.i + value.l);
      let decoded_value;
      switch (value.t) {
        case "int":
          decoded_value = b62_decode_int(encoded_value);
          break;
        case "datetime":
          decoded_value = new Date(b62_decode_int(encoded_value) * 1000);
          break;
        case "str":
          decoded_value = decode(encoded_value);
          break;
        case "NoneType":
          decoded_value = null;
          break;
        case "float":
          decoded_value = b62_decode_np_float_32(encoded_value);
          break;
        default:
          throw new Error(value.t);
      }
      toReturn[key] = decoded_value;
    } else {
      toReturn[key] = value;
    }
  }
  return toReturn;
};
