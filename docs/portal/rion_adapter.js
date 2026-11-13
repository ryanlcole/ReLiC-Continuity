"use strict";

/**
 * Bounded, independent Rion bit-lane ADAPTER for the portal.
 *
 * Three bits per lane: [knownness, sign, value].
 *   knownness: 1 = browser has an API-availability observation, 0 = unknown/unsupported
 *   sign: 0 = non-negative choice/state; reserved for future signed data
 *   value: 1 = selected, 0 = not selected
 *
 * Do not confuse this with the private original RuneCore engine or a generalized
 * Rion physics interpreter. A reversible XOR bit flip is tested here only as a
 * small example of the previously documented experimental bit approach.
 */
(function attach(root) {
  const bit = (x) => x === 0 || x === 1;
  function encodeLane(knownness, sign, value) {
    if (![knownness, sign, value].every(bit)) throw new TypeError("Rion lanes accept explicit 0/1 bits only");
    if (knownness === 0 && value !== 0) throw new RangeError("Unknown lanes cannot claim selected");
    return (knownness << 2) | (sign << 1) | value;
  }
  function decodeLane(encoded) {
    if (!Number.isInteger(encoded) || encoded < 0 || encoded > 7) throw new RangeError("Invalid three-bit lane");
    return Object.freeze({ knownness: (encoded >> 2) & 1, sign: (encoded >> 1) & 1, value: encoded & 1 });
  }
  function flipKnownValue(encoded, mask) {
    const r = decodeLane(encoded);
    if (!bit(mask)) throw new TypeError("XOR mask must be one bit");
    return r.knownness === 1 ? (encoded ^ mask) : encoded;
  }
  function pack(lanes) {
    if (!Array.isArray(lanes) || lanes.length > 256) throw new RangeError("Invalid bounded lane list");
    return lanes.map(({ known, sign, selected }) => encodeLane(known, sign, selected).toString(2).padStart(3, "0")).join(" ");
  }
  root.ReLiCRionAdapter = Object.freeze({ version: "RION-DEMO-v1", encodeLane, decodeLane, flipKnownValue, pack });
})(typeof window === "object" ? window : globalThis);
