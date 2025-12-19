export type Matrix = Float64Array[]

export function makeMatrix(nRows: number, nCols: number): Matrix {
	const buffer = new Float64Array(nRows * nCols)
	const result = new Array<Float64Array>(nRows)
	for (let i = 0; i < nRows; ++i) {
		result[i] = buffer.subarray(nCols * i, nCols * i + nCols)
	}
	return result
}

export function makeTriangular(nRows: number): Matrix {
	const buffer = new Float64Array((nRows * (nRows + 1)) >>> 1)
	const result = new Array<Float64Array>(nRows)
	let ptr = 0
	for (let i = 0; i < nRows; ++i) {
		const len = nRows - i
		result[i] = buffer.subarray(ptr, ptr + len)
		ptr += len
	}
	return result
}

export default class CholeskySolver {
	private constructor(
		public U: Matrix,
		public Y: Matrix,
	) {}

	static init(xCols: number, yCols: number, lambda: number) {
		const L = makeTriangular(xCols)
		const Y = makeMatrix(yCols, xCols)

		const d = Math.sqrt(lambda)
		for (let i = 0; i < xCols; ++i) {
			L[i][0] = d
		}

		return new CholeskySolver(L, Y)
	}

	update(x: Float64Array, y: Float64Array) {
		for (let i = 0; i < y.length; ++i) {
			for (let j = 0; j < x.length; ++j) {
				this.Y[i][j] += x[j] * y[i]
			}
		}

		let w = x.slice()
		let b = 1

		for (let i = 0; i < x.length; ++i) {
			const li = this.U[i][0]
			const wi = w[i]
			const l2 = li * li
			const w2 = wi * wi
			const gamma = b * l2 + w2
			const l_ii = Math.sqrt(l2 + w2 / b)

			const r1 = wi / li
			const r2 = l_ii / this.U[i][0]
			const r3 = (l_ii * w[i]) / gamma

			for (let j = i + 1; j < x.length; ++j) {
				w[j] -= r1 * this.U[i][j - i]
				this.U[i][j - i] = r2 * this.U[i][j - i] + r3 * w[j]
			}

			this.U[i][0] = l_ii
			b += w2 / l2
		}
	}

	solve(): Matrix {
		const n = this.U.length
		const m = this.Y.length
		const result = makeMatrix(m, n)

		for (let col = 0; col < m; ++col) {
			for (let i = 0; i < n; ++i) {
				let sum = this.Y[col][i]
				for (let k = 0; k < i; ++k) {
					sum -= this.U[k][i - k] * result[col][k]
				}
				result[col][i] = sum / this.U[i][0]
			}

			for (let i = n - 1; i >= 0; --i) {
				let sum = result[col][i]
				for (let k = i + 1; k < n; ++k) {
					sum -= this.U[i][k - i] * result[col][k]
				}
				result[col][i] = sum / this.U[i][0]
			}
		}

		return result
	}
}
