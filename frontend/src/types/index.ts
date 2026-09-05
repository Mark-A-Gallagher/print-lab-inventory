// types/index.ts
//
// Mirrors backend Pydantic schemas (app/schemas/*.py). Keep these in
// sync manually - see DESIGN.md Section 9 for the API surface.
//
// TODO: define a Spool interface matching SpoolOut - remember it
//   includes DERIVED fields (current_weight, current_machine_id,
//   reserved_amount, available), not just stored columns.
//
// TODO: define a Machine interface matching MachineOut.
//
// TODO: define a PrintRequest interface matching PrintRequestOut.
//
// TODO: define request-body types (SpoolCreate, MachineCreate,
//   PrintRequestCreate) matching your backend schemas.
