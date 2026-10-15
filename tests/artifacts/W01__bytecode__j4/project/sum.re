let total = [| Part0.answer, Part1.answer, Part2.answer, Part3.answer, Part4.answer, Part5.answer, Part6.answer, Part7.answer, Part8.answer, Part9.answer, Part10.answer, Part11.answer |] |> Array.fold_left((a, b) => a + b, 0);
print_int(total); print_newline();
