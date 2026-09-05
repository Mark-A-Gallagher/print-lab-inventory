// api/client.ts
//
// Thin typed fetch wrappers around the FastAPI backend. DESIGN.md
// Section 9 lists the full endpoint set this should eventually cover.
//
// TODO: a base request() helper that wraps fetch(), sets JSON headers,
//   and throws on non-OK responses.
//
// TODO: getSpools(), getSpool(id), updateSpoolWeight(id, ...),
//   assignSpoolToMachine(id, machineId), getMachines(),
//   createPrintRequest(...), reserveForRequest(id, ...),
//   fulfillRequest(id), etc. - one function per backend endpoint.
