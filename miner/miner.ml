open Async;;

(* Make request and return response or status code *)

let request (url_str : string) (verb : string) (body : string) =
  let url = Uri.of_string url_str in
  let headers = Cohttp.Header.prepend_user_agent (Cohttp.Header.of_list [] (*[ "connection", "close"]*)) "worker" in
  let meth = Cohttp.Code.method_of_string verb in
    try_with (fun () -> Cohttp_async.Client.call meth ~headers ~body:Cohttp_async.Body.(of_string body) url
    >>= fun (res, body) ->
    let http_code = Cohttp.Response.status res in
    match http_code with
    | `OK -> Cohttp_async.Body.to_string body
    | _ -> return "400" (* bad url *)
  ) >>| function
      | Ok s -> s
      | Error _ -> "500" (* request failed *)
;;


(* Double SHA-256 *)

let dHash data =
    data |> Sha256.string |> Sha256.to_bin |> Sha256.string |> Sha256.to_hex
;;


(* Calculate Merkle Root *)

let rec calculateMerkleRow txns = 
    match txns with
    | [] -> []
    | a::b::lst -> dHash (String.concat [a; b]) :: calculateMerkleRow lst
    | a::[] -> [dHash(String.concat [a; a])]
;;

let rec calculateMerkleRoot txns = 
    match txns with
    | a::[] -> a
    | a::b::lst -> calculateMerkleRoot (calculateMerkleRow txns)
    | [] -> ""
;;


(* Increment coinbase txn nonce *)

(*
    # construct block header using values from template

    version = 2 # block version number
    hashPrevBlock = "" # 256 bits
    hashMerkleRoot = "" # 256 bits
    time = int(time())
    #bits = # target in compact format
    nonce = 0
*)

(* hash, update nonce, repeat *)
(* keep track of best hash found for ppow *)


(* share submit format:*)
let share = "000003c48a294584f90e58325c60ca82896d071826b45680a661cec4d42";;
let share_msg = String.concat [{|{"id": 0, "method": "submitblock", "params": ["|};share; {|"]}|}];;

    (*
     '020000003c48a294584f90e58325c60ca82896d071826b45680a661cec4d424d00000000
de6433d46c0c7f50d84a05aec77be0199176cdd47f77e344b6f50c84380fddba66dc47501d00ff
ff0000010001010000000100000000000000000000000000000000000000000000000000000000
00000000ffffffff1302955d0f00456c6967697573005047dc66085fffffffff02fff1052a0100
00001976a9144ebeb1cd26d6227635828d60d3e0ed7d0da248fb88ac01000000000000001976a9147c866aee1fa2f3b3d5effad576df3dbf1f07475588ac00000000']}"
*)

let url = "https://127.0.0.1:8000/submit?val=hi";;
let initial_request = "{'id': 0, 'method': 'getblocktemplate', 'params': [{'capabilities': ['coinbasetxn', 'workid', 'coinbase/append']}]}";;

request "https://127.0.0.1:8000/submit" "POST" share_msg;;
(*request "https://127.0.0.1:8000/fetch" "GET" "hi";;*)

p
(*let () = 
    (*print_endline (hash "hello");*)
    let res = request "https://127.0.0.1" "workerID" "POST" share in
      print_endline res;;
    
    don't_wait_for (exit 0);
    Core.never_returns (Scheduler.go ())
;;*)
